#!/usr/bin/env python3

# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import collections
import glob
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import flask

R_GPU = re.compile('GPU\s+(?P<id>\d+):\s+(?P<model>.+)')

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', help='Port to use for this service.',
                    type=int, default=3390)
parser.add_argument('--gpus', help='List of GPUs to use (inclusive).',
                    type=str, default='0-255')
parser.add_argument('--logdir', help='Directory to store logs.',
                    type=str, default='gpumux')
parser.add_argument('--path', help='Folder where to run jobs..',
                    type=str, default='.')
parser.add_argument('--py', help='Path to custom python interpreter.',
                    type=str, default='')
args = parser.parse_args()
PATH = os.path.abspath(args.path)
PENDING_JOBS = os.path.join(PATH, args.logdir, 'pending_jobs.txt')
RUNNING_PATH = os.path.join(PATH, args.logdir, 'running')
COMPLETED_PATH = os.path.join(PATH, args.logdir, 'completed')

SCREEN_RC = 'logfile %d.log\n'
BASH_CMD = """#!/bin/bash

pushd """ + PATH + """
CUDA_VISIBLE_DEVICES=%(gpu)s PYTHONPATH=. """ + args.py + """ ./%(cmd)s
status=$?
popd
echo $status > %(status)s
"""


def apply_gpu_preferences(detected):
    gmin, gmax = map(int, args.gpus.split('-'))
    to_del = [x for x in detected.keys() if x < gmin or x > gmax]
    while to_del:
        del detected[to_del.pop()]
    return detected


def get_gpus():
    cmd_outut = subprocess.check_output(['nvidia-smi', '--list-gpus']).decode()
    gpus = collections.OrderedDict()
    for x in cmd_outut.split('\n'):
        if not x:
            continue
        expr = R_GPU.match(x)
        gpus[int(expr.group('id'))] = expr.group('model')

    gpus = apply_gpu_preferences(gpus)
    print('GPUs available %d' % len(gpus))
    for k, v in gpus.items():
        print('%-2d %s' % (k, v))
    return gpus


class MyFlask(flask.Flask):
    jinja_options = flask.Flask.jinja_options.copy()
    jinja_options.update(dict(block_start_string='<%',
                              block_end_string='%>',
                              variable_start_string='${',
                              variable_end_string='}',
                              comment_start_string='<#',
                              comment_end_string='#>', ))


class Jobs:
    CAST = dict(gpu=int, status=int, cmd=str)

    def __init__(self):
        self.pending = [x for x in open(PENDING_JOBS, 'r').read().split('\n')
                        if x]
        self.running = self.parse_jobs(RUNNING_PATH)
        self.completed = self.parse_jobs(COMPLETED_PATH)
        self.pending_update = []

    def refresh(self):
        if self.pending_update:
            open(PENDING_JOBS, 'w').write(self.pending_update.pop())
            while self.pending_update:
                self.pending_update.pop()
        self.pending = [x for x in open(PENDING_JOBS, 'r').read().split('\n')
                        if x]
        self.running = self.parse_jobs(RUNNING_PATH)
        to_complete = [x for x in self.running if x.status is not None]
        if to_complete:
            self.running = [x for x in self.running if x not in to_complete]
            for x in to_complete:
                x.complete()
        self.completed = self.parse_jobs(COMPLETED_PATH)
        update_pending_file = False
        while self.schedule():
            update_pending_file = True
        if update_pending_file:
            open(PENDING_JOBS, 'w').write('\n'.join(self.pending))

    def schedule(self):
        if not self.pending:
            return False
        gpu_used = set([x.gpu for x in self.running])
        gpu_all = set(GPUS.keys())
        gpu_free = gpu_all - gpu_used
        if not gpu_free:
            return False
        gpu = list(gpu_free)[0]
        id = 0
        if self.running or self.completed:
            id = max(x.id for x in self.running + self.completed)
        id += 1
        cmd = self.pending.pop(0)
        j = Job(id, gpu, cmd, None)
        self.running.append(j)
        return True

    @classmethod
    def parse_jobs(cls, folder):
        logs = set(
            map(os.path.basename, glob.glob(os.path.join(folder, '*.*'))))
        ids = sorted(set(int(x.split('.')[0]) for x in logs))
        jobs = []
        for x in ids:
            params = {}
            for key, cast in cls.CAST.items():
                params[key] = None
                if str(x) + '.' + key in logs:
                    params[key] = cast(
                        open(os.path.join(folder, str(x) + '.' + key),
                             'r').read())
            jobs.append(Job(x, **params))
        return jobs


class Job:
    def __init__(self, id, gpu, cmd, status):
        self.id = id
        self.gpu = gpu
        self.cmd = cmd
        self.status = status
        if gpu is not None and status is None and not self.is_running():
            # Jobs that were interrupted by a reboot or some other action.
            self.spawn()
        self.running_time = self.compute_running_time()

    @property
    def screen_id(self):
        return 'gpumux_%d' % self.id

    @property
    def json(self):
        return dict(id=self.id, gpu=self.gpu, cmd=self.cmd, status=self.status,
                    time=self.running_time)

    def is_running(self):
        if self.id is None:
            return False
        screens = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE)
        return self.screen_id in screens.stdout.decode()

    def compute_running_time(self):
        if not os.path.exists(os.path.join(RUNNING_PATH, '%d.gpu' % self.id)):
            path = COMPLETED_PATH
        else:
            path = RUNNING_PATH
        start_time = os.path.getmtime(os.path.join(path, '%d.gpu' % self.id))
        if path == RUNNING_PATH:
            return round(time.time() - start_time)
        end_time = os.path.getmtime(os.path.join(path, '%d.status' % self.id))
        return round(end_time - start_time)

    def spawn(self):
        assert self.status is None
        bash_cmd = BASH_CMD % dict(cmd=self.cmd, gpu=self.gpu,
                                   status='%d.status' % self.id)
        open(os.path.join(RUNNING_PATH, '%d.gpu' % self.id), 'w').write(
            str(self.gpu) + '\n')
        open(os.path.join(RUNNING_PATH, '%d.cmd' % self.id), 'w').write(
            str(self.cmd) + '\n')
        open(os.path.join(RUNNING_PATH, '%d.sh' % self.id), 'w').write(bash_cmd)
        open(os.path.join(RUNNING_PATH, '%d.screenrc' % self.id), 'w').write(
            SCREEN_RC % self.id)
        os.chmod(os.path.join(RUNNING_PATH, '%d.sh' % self.id), 0o700)
        popen = subprocess.Popen(['screen', '-dm', '-L',
                                  '-S', self.screen_id,
                                  '-c', '%d.screenrc' % self.id,
                                  './%d.sh' % self.id],
                                 cwd=RUNNING_PATH)
        status = popen.wait()
        assert status == 0

    def complete(self):
        assert self.status is not None
        files = glob.glob(os.path.join(RUNNING_PATH, '%d.*' % self.id))
        for x in files:
            shutil.move(x, os.path.join(COMPLETED_PATH, os.path.basename(x)))


HOST = socket.gethostname()
GPUS = get_gpus()
app = MyFlask(__name__)


@app.route('/')
def home():
    return flask.render_template('home.html', host=HOST, path=PATH,
                                 gpus=len(GPUS), python=args.py or 'default')


@app.route('/status.json')
def status():
    return flask.jsonify(job_thread=JOB_THREAD.is_alive(),
                         completed_jobs=[x.json for x in JOBS.completed][::-1],
                         running_jobs=[x.json for x in JOBS.running],
                         pending_jobs='\n'.join(JOBS.pending))


@app.route('/queue/update.json', methods=['POST'])
def queue_update():
    pending = flask.request.json['pending']
    JOBS.pending_update.append(pending)
    return flask.jsonify(pending=pending)


@app.route('/job/<job_id>')
def job_log(job_id):
    if os.path.exists(os.path.join(RUNNING_PATH, '%s.log' % job_id)):
        fn = os.path.join(RUNNING_PATH, '%s.log' % job_id)
    elif os.path.exists(os.path.join(COMPLETED_PATH, '%s.log' % job_id)):
        fn = os.path.join(COMPLETED_PATH, '%s.log' % job_id)
    else:
        flask.abort(404)
    return flask.Response(open(fn, 'r').read(), mimetype='text/plain')


def job_thread():
    print('Starting jobs manager.')
    while True:
        JOBS.refresh()
        time.sleep(1)


print(RUNNING_PATH)
os.makedirs(RUNNING_PATH, exist_ok=True)
os.makedirs(COMPLETED_PATH, exist_ok=True)
if not os.path.exists(PENDING_JOBS):
    open(PENDING_JOBS, 'w').write('')
JOBS = Jobs()
JOB_THREAD = threading.Thread(target=job_thread)


def main():
    JOB_THREAD.start()
    app.run(port=args.port)


if __name__ == '__main__':
    main()
