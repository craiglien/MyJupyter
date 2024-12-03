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

PORT=${JUPYTER_PORT:-8888}

if [ -n "$START_SHELL" ]; then
  # If TERM is set, it usually indicates an interactive session, so start an interactive shell
  exec gosu ${U} /bin/bash
else
  exec gosu ${U} jupyter notebook --ip=0.0.0.0 --port=${PORT} --no-browser --allow-root --NotebookApp.token=''
fi
