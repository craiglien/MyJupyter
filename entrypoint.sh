#!/bin/bash

U=crun
G=${U}

USER_ID=${LOCAL_UID:-1000}
GROUP_ID=${LOCAL_GID:-1000}

existing_group=$(getent group $GROUP_ID | cut -d: -f1)
if [ -n "$existing_group" ]; then
  groupmod -n ${G} $existing_group
else
  groupadd -g $GROUP_ID ${G}
fi


existing_user=$(getent passwd $USER_ID | cut -d: -f1)
if [ -n "$existing_user" ]; then
  usermod -l ${U} $existing_user
  usermod -d /home/${U} -m ${U}
else
  # Create the user if it doesn't already exist
  useradd -m -u $USER_ID -g ${G} -s /bin/bash ${U}
fi

chown ${U}:${G} /app

JUPYTER_PORT_VAL=${JUPYTER_PORT:-8888}
MARIMO_PORT_VAL=${MARIMO_PORT:-8889}

#gosu ${U} id
#gosu ${U} ls -l /app
#echo gosu ${U} jupyter notebook --ip=0.0.0.0 --port=${JUPYTER_PORT_VAL} --no-browser --allow-root
#/bin/bash

# Two long-running servers now share the container, so this can no longer be
# a single `exec`. Background both under gosu, forward TERM/INT to both PIDs
# so `docker stop`/Ctrl-C still shuts down cleanly, and bring the container
# down if either process dies unsupervised rather than limping along with
# just one server up.
gosu ${U} jupyter notebook --ip=0.0.0.0 --port=${JUPYTER_PORT_VAL} --no-browser --allow-root --NotebookApp.token='' &
JUPYTER_PID=$!

gosu ${U} marimo edit /app/game_marimo.py --headless --no-token --host 0.0.0.0 --port ${MARIMO_PORT_VAL} &
MARIMO_PID=$!

trap 'kill -TERM $JUPYTER_PID $MARIMO_PID 2>/dev/null' TERM INT
wait -n $JUPYTER_PID $MARIMO_PID
