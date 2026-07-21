TOP_DIR:=$(shell pwd)
DESTDIR=/
PYFLAKES = $(shell { command -v pyflakes-3 || command -v pyflakes3 || command -v pyflakes; }  2> /dev/null)
BLACK := $(shell { command -v black; } 2> /dev/null)
ISORT := $(shell { command -v isort; } 2> /dev/null)
PYTHON=/usr/bin/python3

all: clean build


clean:
	@echo "cleaning: python bytecode"
	@rm -f *.pyc
	@rm -f koan/*.pyc
	@echo "cleaning: build artifacts"
	@rm -f koan/_version.py
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
	@if python3 -c "from importlib.metadata import version; from sys import exit; exit(0 if tuple(int(p) for p in version('setuptools_scm').split('.')[:2]) >= (8, 2) else 1)" 2>/dev/null; then \
		${PYTHON} -m setuptools_scm --force-write-version-files > /dev/null; \
	else \
		${PYTHON} setup.py --version > /dev/null 2>&1; \
	fi
	@cd docs; make html

qa:
ifeq ($(strip $(PYFLAKES)),)
	@echo "No pyflakes found"
else
	@echo "checking: pyflakes ${PYFLAKES}"
	@${PYFLAKES} *.py koan/*.py
endif

ifeq ($(strip $(BLACK)),)
	@echo "No black found"
else
	@echo "checking: black"
	@${BLACK} --verbose --safe .
endif

ifeq ($(strip $(ISORT)),)
	@echo "No isort found"
else
	@echo "checking: isort ${ISORT}"
	@${ISORT} --check-only --diff --profile black .
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

# koan.spec hardcodes Version, which rpmbuild uses to compute Source0's expected filename before dist/ exists.
# Sync it to the version the sdist we just built actually has (read from its filename, since re-deriving the version via
# a second setuptools_scm call can disagree with the first once the sdist step leaves the tree dirty), or the expected
# and actual tarball names diverge whenever HEAD isn't exactly on a release tag.
pin-spec-version: release
	@sed -ri 's/^(Version:[[:space:]]*).*/\1'"$$(basename dist/*.tar.gz .tar.gz | sed 's/^koan-//')"'/' koan.spec

rpms: pin-spec-version
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

# debian/changelog's top entry version is what dpkg-buildpackage uses for the
# built package; sync it to the same setuptools_scm-derived version CI already
# threads through via SETUPTOOLS_SCM_PRETEND_VERSION (mirrors pin-spec-version's
# job for koan.spec's hardcoded Version: field). Native packages (see
# debian/source/format) must not carry a "-<revision>" suffix, or dpkg-source
# mistakes the package for a non-native one and looks for an orig tarball.
debs: authors ## Creates native debs in a directory called deb-build.
	@VERSION="$${SETUPTOOLS_SCM_PRETEND_VERSION:-$$(${PYTHON} -m setuptools_scm)}"; \
	DEBFULLNAME="The Cobbler Authors" DEBEMAIL="cobbler.project@gmail.com" \
	dch --newversion "$$VERSION" --distribution unstable --nomultimaint "Automated build."
	@debuild -us -uc
	@mkdir -p deb-build
	@cp ../koan_* deb-build/

.PHONY: tags
tags:
	find . \( -name build -o -name .git \) -prune -o -type f -name '*.py' -print | xargs etags -o TAGS --
