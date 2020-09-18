#
# RPM spec file for Koan
#
# Supported/tested build targets:
# - Fedora: 30, 31, Rawhide
# - CentOS + EPEL: 7, 8
# - SLE: 11sp4, 12sp3, 15sp1
# - OpenSuSE: Leap 15.1, Tumbleweed
# - Debian: 9, 10
# - Ubuntu: 16.04, 18.04
#
# If it doesn't build on the Open Build Service (OBS) it's a bug.
#


%if 0%{?suse_version} && 0%{?suse_version} < 1500
%bcond_without use_python2
%else
%bcond_with use_python2
%endif

# If they aren't provided by a system installed macro, define them
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?__python3: %global __python3 /usr/bin/python3}

%if %{_vendor} == "debbuild"
%global pyinstflags --no-compile -O0
%global pytargetflags --install-layout=deb
%global develsuffix dev
%else
%global pyinstflags -O1
%global pytargetflags %{nil}
%global develsuffix devel
%endif

%if %{with use_python2}
%global __python %{__python2}
%global py_shbang_opts %{py2_shbang_opts}
%global python_pkgversion %{nil}
%else
%global __python %{__python3}
%global py_shbang_opts %{py3_shbang_opts}
%{!?python3_pkgversion: %global python3_pkgversion 3}
%global python_pkgversion %{python3_pkgversion}
%endif

%{!?py_build: %global py_build CFLAGS="%{optflags}" %{__python} setup.py build}
%{!?py_install: %global py_install %{__python} setup.py install %{?pyinstflags} --skip-build --root %{buildroot} --prefix=%{_prefix} %{?pytargetflags}}

# Always override this definition to unbreak SUSE distributions
%global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")

Name:           koan
Version:        2.9.0
Release:        1%{?dist}
Summary:        Kickstart over a network

%if %{_vendor} == "debbuild"
Packager:       Cobbler Developers <cobbler@lists.fedorahosted.org>
Group:          admin
%else
Group:          Development/Libraries
%endif

License:        GPL-2.0-or-later
URL:            https://github.com/cobbler/koan
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

%if 0%{?suse_version} && 0%{?suse_version} < 1315
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-buildroot
%else
BuildArch:      noarch
%endif

Requires:       python%{python_pkgversion}-koan = %{version}-%{release}

%description
Koan stands for kickstart-over-a-network and allows for both network
installation of new virtualized guests and reinstallation of an existing
system. For use with a boot-server configured with Cobbler.


%package -n python%{python_pkgversion}-koan
Summary:        koan python%{python_pkgversion} module
%if 0%{?suse_version} && 0%{?suse_version} < 1315
Group:          Development/Libraries/Python
%endif
%{?python_provide:%python_provide python%{python_pkgversion}-koan}
BuildRequires:  python%{python_pkgversion}-%{develsuffix}
BuildRequires:  python%{python_pkgversion}-setuptools
%if 0%{?rhel}
# We need these to build this properly, and OBS doesn't pull them in by default for EPEL
BuildRequires:  epel-rpm-macros
%endif
%{?python_enable_dependency_generator}
%if ! (%{defined python_enable_dependency_generator} || %{defined python_disable_dependency_generator})
Requires:       python%{python_pkgversion}-distro
Requires:       python%{python_pkgversion}-netifaces
Requires:       python%{python_pkgversion}-simplejson
%if 0%{?suse_version}
# SUSE distributions have messed up naming of this module
%if 0%{?suse_version} < 1500
Requires:       libvirt-python%{python_pkgversion}
%else
Requires:       python%{python_pkgversion}-libvirt-python
%endif
%else
Requires:       python%{python_pkgversion}-libvirt
%endif
%endif
%if %{_vendor} == "debbuild"
Requires:       virtinst
%else
Requires:       virt-install
%endif

%description -n python%{python_pkgversion}-koan
This package provides the Python module code for Koan.


%prep
%setup -q

%if 0%{?fedora}%{?rhel}
pathfix.py -pni "%{__python} %{py_shbang_opts}" bin
%endif

%build
%py_build

%install
%py_install

%if 0%{?suse_version} && 0%{?suse_version} < 1315
%clean
rm -rf %{buildroot}
%endif

%files
%if 0%{?suse_version} && 0%{?suse_version} < 1315
%{!?_licensedir:%global license %doc}
%defattr(-,root,root,-)
%endif
%license COPYING
%doc README
%{_bindir}/koan
%{_bindir}/cobbler-register

%files -n python%{python_pkgversion}-koan
%if 0%{?suse_version} && 0%{?suse_version} < 1315
%{!?_licensedir:%global license %doc}
%defattr(-,root,root,-)
%endif
%license COPYING
%{python_sitelib}/koan*

%if %{_vendor} == "debbuild"
%post -n python%{python_pkgversion}-koan
# Do late-stage bytecompilation, per debian policy
py%{python_pkgversion}compile -p python%{python_pkgversion}-koan

%preun -n python%{python_pkgversion}-koan
# Ensure all __pycache__ files are deleted, per debian policy
py%{python_pkgversion}clean -p python%{python_pkgversion}-koan
%endif


%changelog
* Sun Nov 24 2019 Neal Gompa <ngompa13@gmail.com>
- Initial rewrite of packaging
