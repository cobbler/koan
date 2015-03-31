
TOP_DIR:=$(shell pwd)
DESTDIR=/


all: clean build


clean:
	@echo "cleaning: python bytecode"
	@rm -f *.pyc
	@rm -f koan/*.pyc
	@echo "cleaning: build artifacts"
	@rm -rf build rpm-build release
	@rm -rf dist
	@rm -f MANIFEST AUTHORS
	@rm -f docs/*.1.gz
	@echo "cleaning: temp files"
	@rm -f *~
	@rm -f *.tmp
	@rm -f *.log
	@echo "cleaning: documentation"
	@cd docs; make clean > /dev/null 2>&1

doc:
	@echo "creating: documentation"
	@cd docs; make html > /dev/null 2>&1

qa:
	@echo "checking: pyflakes"
	@pyflakes *.py bin/koan bin/cobbler-register koan/*.py

	@echo "checking: pep8"
	@pep8 -r --ignore E303,E501 \
        *.py bin/koan bin/cobbler-register koan/*.py

authors:
	@echo "creating: AUTHORS"
	@cp AUTHORS.in AUTHORS
	@git log --format='%aN <%aE>' | grep -v 'root' | sort -u >> AUTHORS

sdist: authors
	@echo "creating: sdist"
	@python setup.py sdist > /dev/null

release: clean qa authors sdist doc
	@echo "creating: release artifacts"
	@mkdir release
	@cp dist/*.gz release/
	@cp koan.spec release/
	@cp debian/koan.dsc release/
	@cp debian/changelog release/debian.changelog
	@cp debian/control release/debian.control
	@cp debian/rules release/debian.rules

nosetests:
	PYTHONPATH=./koan/ nosetests -v -w tests/koan/ 2>&1 | tee test.log

build:
	python setup.py build -f

# Debian/Ubuntu requires an additional parameter in setup.py
install: build
	if [ -e /etc/debian_version ]; then \
		python setup.py install --root $(DESTDIR) -f --install-layout=deb; \
	else \
		python setup.py install --root $(DESTDIR) -f; \
	fi

savestate:
	python setup.py -v savestate --root $(DESTDIR); \


webtest: devinstall
	make clean
	make devinstall


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


.PHONY: tags
tags:
	find . \( -name build -o -name .git \) -prune -o -type f -name '*.py' -print | xargs etags -o TAGS --
