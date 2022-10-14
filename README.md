# Using Windows on Docker 

Go to Command Prompt
To "Docker Desktop Installer.exe" install
If you’re using PowerShell you should run it as:

Start-Process 'Docker Desktop Installer.exe' -Wait install
If using the Windows Command Prompt:

start /w "Docker Desktop Installer.exe" install
The install command accepts the following flags:

* ``--quiet: suppresses information output when running the installer``
* `` --accept-license: accepts the Docker Subscription Service Agreement now, rather than requiring it to be accepted when the application is first run``
*`` --no-windows-containers: disables Windows containers integration``
* ``--allowed-org=<org name>: requires the user to sign in and be part of the specified Docker Hub organization when running the application``
* ``--backend=<backend name>: selects the default backend to use for Docker Desktop, hyper-v, windows or wsl-2 (default)``
The Docker menu (whale menu) displays the Docker Subscription Service Agreement window.

## key points:

* Docker Desktop is free for small businesses (fewer than 250 employees AND less than $10 million in annual revenue), personal use, education, and non-commercial open  source projects.
* Otherwise, it requires a paid subscription for professional use.
* Paid subscriptions are also required for government entities.
* The Docker Pro, Team, and Business subscriptions include commercial use of Docker Desktop.
* Select Accept to continue. Docker Desktop starts after you accept the terms.
