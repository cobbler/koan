#!/bin/bash
# Utility script to run Docker container without building the RPMs,
# just install them. So make sure they are in rpm-build dir!

if [ "$1" == "--with-tests" ]; then
    RUN_TESTS=true
    shift
else
    RUN_TESTS=false
fi

TAG=$1
IMAGE=koan:$TAG

# Launch container and install Koan
echo "==> Start container ..."
docker run -d --name koan -v "$PWD/rpm-build:/usr/src/koan/rpm-build" "$IMAGE" /bin/bash
echo "==> Install fresh RPMs ..."
docker exec -it koan bash -c 'rpm -Uvh rpm-build/koan-*.noarch.rpm'

# Does not work because of wrong exit code. Koan has not help or version switch which means we need to skip this for now
#echo "==> Show Koan version ..."
#docker exec -it koan bash -c 'koan version'

if $RUN_TESTS; then
    echo "==> Running tests ..."
    docker exec -it koan bash -c 'pip3 install coverage distro setuptools sphinx requests netifaces'
    docker exec -it koan bash -c 'pip3 install pyflakes pycodestyle pytest pytest-cov codecov'
    docker exec -it koan bash -c 'pytest'
fi

# Clean up
echo "==> Stop Koan container ..."
docker stop koan
echo "==> Delete Koan container ..."
docker rm koan
