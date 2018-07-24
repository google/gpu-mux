# GPUMux

GPUMux is a scheduler for CUDA GPU python jobs.
**This is not an officially supported Google product.**

You let it know what GPUs to use and it will schedule tasks on them for you, always maximizing
the resources. It lets your spawn tasks directly from the web browser and also permits to track
progress, errors, logs.

If the instance is rebooted or shut down, the jobs are restarted when you launch GPUMux.

## Setup

```bash
virtualenv -p python3 --system-site-packages env3
. env3/bin/activate
pip3 install -r requirements.txt
```

## Usage

**Important**: Make sure the port you use is not open to the world since GPUMux lets you run
arbitrary commands, anyone connecting to the port can run arbitrary commands. You can verify this
easily by checking that you cannot access GPUMux remotely without ssh port forwarding.


In the folder you want to run jobs in, start GPUMux:

```bash
# On your remote machine where the tasks will run.
./gpumux.py --port 3390 --path <path where to run jobs> --py <path to your custom python>
```

This command launches GPUMux in the local folder.
- *port* is the port to run on.
- *path* is the path where you jobs will run and executable(s) will be found.
- *py* is the python interpreter to use
  - Defaults installs are `/env/bin/python` or `/env/bin/python3`.
  - For Conda, type `which python` in your Conda environment.
  - For virtualenv, type `which python` in your virtualenv.


If you're running on cloud, you'll need to forward the port to your local machine:
```bash
# Run on your local machine.
ssh -L 3390:localhost:3390 username@instance
```

If you're running multiple instances, you will want to forward to different local ports:
```bash
# Run each on command in a different terminal on your local machine.
ssh -L 3390:localhost:3390 username1@instance1
ssh -L 3391:localhost:3390 username2@instance2
...
```

Then simply point your browser to the port:
```bash
# On your local machine.
http://localhost:3390
# And if you have more.
http://localhost:3391
```

## Files

Files are saved in a locally created gpumux folder.
You can see the logs of your past runs, status codes, commands. 

## Jobs

If you wish to, you can access your running jobs with the command screen:
```bash
screen -dr gpumux_<job id>
```
