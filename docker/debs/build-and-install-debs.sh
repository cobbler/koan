#!/bin/bash
# Utility script to build DEBs in a Docker container and then install them

set -euo pipefail

if [ "$1" == "--with-tests" ]; then
    RUN_TESTS=true
    shift
else
    RUN_TESTS=false
fi

TAG=$1
DOCKERFILE=$2

IMAGE=koan:$TAG

# Build container
echo "==> Build container ..."
docker build -t "$IMAGE" -f "$DOCKERFILE" .

# Build DEBs
echo "==> Build packages ..."
mkdir -p deb-build tmp
docker run --rm -ti -v "$PWD/deb-build:/usr/src/koan/deb-build" -v "$PWD/tmp:/var/tmp" "$IMAGE"

# Launch container and install Koan
echo "==> Start container ..."
docker run -t -d --name koan -v "$PWD/deb-build:/usr/src/koan/deb-build" "$IMAGE" /bin/bash

echo "==> Install fresh packages ..."
docker exec -it koan bash -c 'dpkg -i deb-build/DEBS/all/koan*.deb'

# Does not work because of wrong exit code. Koan has not help or version switch which means we need to skip this for now
#echo "==> Wait 5 sec. and show Koan version ..."
#docker exec -it koan bash -c 'koan'

if $RUN_TESTS; then
    # Almost all of these requirement are already satisfied in the Dockerfiles!
    echo "==> Running tests ..."
    docker exec -it koan bash -c 'pip3 install coverage distro setuptools sphinx netaddr distro'
    docker exec -it koan bash -c 'pip3 install pyflakes pycodestyle pytest pytest-cov codecov'
    docker exec -it koan bash -c 'pytest-3'
fi

# Clean up
echo "==> Stop Koan container ..."
docker stop koan
echo "==> Delete Koan container ..."
docker rm koan
rm -rf ./tmp
