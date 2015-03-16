#
# RPM spec file for Koan
#
# Supported/tested build targets:
# - Fedora: 20, 19, 18
# - RHEL: 6, 5, 4
# - CentOS: 6, 5
# - SLES: 11sp3, 11sp2, 10
# - OpenSuSE: Factory, 13.1, 12.3, 12.2
#
# If it doesn't build on the Open Build Service (OBS) it's a bug.
# https://build.opensuse.org/project/subprojects/home:libertas-ict
#

%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

%global debug_package %{nil}
%define _binaries_in_noarch_packages_terminate_build 1
%define _unpackaged_files_terminate_build 1

%define name koan
%define version 2.9.0
%define unmangled_version 2.9.0
%define release 1

Summary: Libraries and tools to manage device registration in Zenoss
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: GPLv2
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
Vendor: Jorgen Maas <jorgen.maas@gmail.com>
Url: http://github.com/cobbler/koan

%if %{?suse_version: %{suse_version} > 1110} %{!?suse_version:1}
BuildArchitectures: noarch
%endif

BuildRequires: python >= 2.3
Requires: python >= 2.3

%if 0%{?suse_version} == 1010
BuildRequires: python-devel
%endif


%description
bla 
bla bla

bla


%prep
%setup -n %{name}-%{unmangled_version}

%build
%{__python} setup.py build

%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --prefix=%{_prefix} --root=%{buildroot} --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
%{python_sitelib}/*
#%dir /etc/zenossctl
#%config(noreplace) %attr(640,root,root) /etc/zenossctl/zenossctl.json
%doc README AUTHORS COPYING

%changelog
* Wed Apr 09 2014 Jörgen Maas <jorgen.maas@gmail.com>
- 1.0.0 - Initial release

# EOF
