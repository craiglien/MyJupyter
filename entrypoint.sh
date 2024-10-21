#!/bin/bash

U=crun
G=${U}

USER_ID=${LOCAL_UID:-1000}
GROUP_ID=${LOCAL_GID:-1000}

groupadd -g $GROUP_ID ${G}
useradd -m -u $USER_ID -g ${G} -s /bin/bash ${U}

PORT=${JUPYTER_PORT:-8888}

exec gosu ${U} jupyter notebook --ip=0.0.0.0 --port=${PORT} --no-browser --allow-root
