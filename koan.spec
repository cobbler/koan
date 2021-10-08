#
# RPM spec file for Koan
#
# Supported/tested build targets:
# - Fedora: 30, 31, Rawhide
# - CentOS + EPEL: 7, 8
# - SLE: 11sp4, 12sp3, 15sp1
# - openSUSE: Leap 15.1, Tumbleweed
# - Debian: 9, 10
# - Ubuntu: 16.04, 18.04
#
# If it doesn't build on the Open Build Service (OBS) it's a bug.
#

# If they aren't provided by a system installed macro, define them
%{!?__python3: %global __python3 /usr/bin/python3}

%if "%{_vendor}" == "debbuild"
%global pyinstflags --no-compile -O0
%global pytargetflags --install-layout=deb
%global develsuffix dev
%else
%global pyinstflags -O1
%global pytargetflags %{nil}
%global develsuffix devel
%endif

%global __python %{__python3}
%global py_shbang_opts %{py3_shbang_opts}
%{!?python3_pkgversion: %global python3_pkgversion 3}
%global python_pkgversion %{python3_pkgversion}

%{!?py_build: %global py_build CFLAGS="%{optflags}" %{__python} setup.py build}
%{!?py_install: %global py_install %{__python} setup.py install %{?pyinstflags} --skip-build --root %{buildroot} --prefix=%{_prefix} %{?pytargetflags}}

# Always override this definition to unbreak SUSE distributions
%global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")

Name:           koan
Version:        3.0.2
Release:        1%{?dist}
Summary:        Kickstart over a network

%if "%{_vendor}" == "debbuild"
Packager:       Cobbler Developers <cobbler@lists.fedorahosted.org>
Group:          admin
%else
Group:          Development/Libraries
%endif

License:        GPL-2.0-or-later
URL:            https://github.com/cobbler/koan
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python%{python_pkgversion}-%{develsuffix}
BuildRequires:  python%{python_pkgversion}-setuptools
%if 0%{?rhel}
# We need these to build this properly, and OBS doesn't pull them in by default for EPEL
BuildRequires:  epel-rpm-macros
%endif
Requires:       python%{python_pkgversion}-distro
Requires:       python%{python_pkgversion}-netifaces
%if 0%{?suse_version}
# SUSE distributions have messed up naming of this module
Requires:       python%{python_pkgversion}-libvirt-python
%else
Requires:       python%{python_pkgversion}-libvirt
%endif
%if "%{_vendor}" == "debbuild"
Recommends:     virtinst
%else
Recommends:     virt-install
%endif

%description
Koan stands for kickstart-over-a-network and allows for both network
installation of new virtualized guests and reinstallation of an existing
system. For use with a boot-server configured with Cobbler.

%prep
%setup -q

%if 0%{?fedora}%{?rhel}
pathfix.py -pni "%{__python} %{py_shbang_opts}" bin
%endif

%build
%py_build

%install
%py_install

%files
%license COPYING
%doc README.md
%{_bindir}/koan
%{_bindir}/cobbler-register
%{python_sitelib}/koan*

%if "%{_vendor}" == "debbuild"
%post
# Do late-stage bytecompilation, per debian policy
py%{python_pkgversion}compile -p %{name}

%preun
# Ensure all __pycache__ files are deleted, per debian policy
py%{python_pkgversion}clean -p %{name}
%endif


%changelog
* Sun Nov 24 2019 Neal Gompa <ngompa13@gmail.com>
- Initial rewrite of packaging
