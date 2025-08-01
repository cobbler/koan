TOP_DIR:=$(shell pwd)
DESTDIR=/
PYFLAKES = $(shell { command -v pyflakes-3 || command -v pyflakes3 || command -v pyflakes; }  2> /dev/null)
BLACK := $(shell { command -v black; } 2> /dev/null)
PYTHON=/usr/bin/python3

all: clean build


clean:
	@echo "cleaning: python bytecode"
	@rm -f *.pyc
	@rm -f koan/*.pyc
	@echo "cleaning: build artifacts"
	@rm -rf build
	@rm -rf rpm-build/*
	@rm -rf deb-build/*
	@rm -rf release
	@rm -rf dist
	@rm -f MANIFEST AUTHORS
	@rm -f docs/*.1.gz
	@echo "cleaning: temp files"
	@rm -f *~
	@rm -f *.tmp
	@rm -f *.log
	@echo "cleaning: documentation"
	@cd docs; make clean

doc:
	@echo "creating: documentation"
	@cd docs; make html

qa:
ifeq ($(strip $(PYFLAKES)),)
	@echo "No pyflakes found"
else
	@echo "checking: pyflakes ${PYFLAKES}"
	@${PYFLAKES} *.py bin/koan bin/cobbler-register koan/*.py
endif

ifeq ($(strip $(BLACK)),)
	@echo "No black found"
else
	@echo "checking: black"
	@${BLACK} --verbose --safe .
endif

authors:
	@echo "creating: AUTHORS"
	@cp AUTHORS.in AUTHORS
	@git log --format='%aN <%aE>' | grep -v 'root' | sort -u >> AUTHORS

sdist: authors
	@echo "creating: sdist"
	${PYTHON} -m build --sdist

bdist: authors
	@echo "creating: bdist"
	${PYTHON} -m build

release: clean qa authors sdist bdist doc
	@echo "creating: release artifacts"
	@mkdir release
	@cp dist/*.gz release/
	@cp koan.spec release/

nosetests:
	PYTHONPATH=./koan/ nosetests -v -w tests/cli/ 2>&1 | tee test.log

build:
	${PYTHON} -m pip wheel -f .

# Debian/Ubuntu requires an additional parameter in setup.py
install: build
	if [ -e /etc/debian_version ]; then \
		${PYTHON} -m build --root $(DESTDIR) -f --install-layout=deb; \
	else \
		${PYTHON} -m build --root $(DESTDIR) -f; \
	fi

rpms: release
	mkdir -p rpm-build
	cp dist/*.gz rpm-build/
	rpmbuild --define "_topdir %(pwd)/rpm-build" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define "_specdir %{_topdir}" \
	--define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
	--define "_sourcedir  %{_topdir}" \
	-ba koan.spec

# Only build a binary package
debs: release ## Runs the target release and then creates via debbuild the debs in a directory called deb-build.
	mkdir -p deb-build
	mkdir -p deb-build/{BUILD,BUILDROOT,DEBS,SDEBS,SOURCES}
	cp dist/*.gz deb-build/
	debbuild --define "_topdir %(pwd)/deb-build" \
	--define "_builddir %{_topdir}" \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir  %{_topdir}" \
	-vv -bb koan.spec

.PHONY: tags
tags:
	find . \( -name build -o -name .git \) -prune -o -type f -name '*.py' -print | xargs etags -o TAGS --
