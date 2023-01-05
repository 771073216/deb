import json
import os
import shutil

import requests
import yaml

conf_file = open('deb.yaml', encoding='utf-8')
conf = yaml.load(conf_file, Loader=yaml.Loader)
version_file = open('version.json', 'r', encoding='utf-8')
ver_conf = json.load(version_file)
global update_flag, commit

def add_space(strs,number):
    k=''
    m=0
    for i in strs:
        k+=' '*number+i
        m = m + 1
        if m < len(strs):
            k +='\n'
    return k

def download_file(url, file_name):
    res = requests.get(url)
    file = open('tmp/' + file_name, 'wb')
    file.write(res.content)
    file.close()


def run_build_command(name):
    build_command = conf['dist'][name]['build_command']
    os.system('bash ' + build_command)


def check_version(programs, nums):
    global update_flag, commit
    update_flag = 0
    commit = ''
    for i in programs:
        url = conf['dist'][i]['url']
        repo = url.split('/')[3] + '/' + url.split('/')[4]
        gh_api = requests.get('https://api.github.com/repos/' + repo + '/releases/latest').text
        remote_version = str(json.loads(gh_api)['tag_name']).replace('v', '')
        local_version = ver_conf[i]
        if remote_version == local_version:
            continue
        update_flag = 1
        ver_conf[i] = remote_version
        version_file_w = open('version.json', 'w', encoding='utf-8')
        json.dump(ver_conf, version_file_w, sort_keys=True, indent=0)
        version_file_w.close()
        commit += '"' + i + ': v' + local_version + ' -> v' + remote_version + ' "'
    if update_flag == 1:
        main(nums)


def expand_file(zip_type, name, file_name):
    if zip_type[0] == 'unzip':
        os.system('unzip tmp/' + file_name + ' ' + conf['dist'][name]['expand']['unzip']['file'] + ' -d tmp/')
        out_path = 'tmp/' + conf['dist'][name]['expand']['unzip']['file']
    else:
        os.system(
            'tar --no-same-owner -C tmp/ -xf tmp/' + file_name + ' ' + conf['dist'][name]['expand']['tar_gz']['file'])
        out_path = 'tmp/' + conf['dist'][name]['expand']['tar_gz']['file']
    return out_path


def check_dir(path):
    is_dir = os.path.exists(path)
    if not is_dir:
        os.makedirs(path)


def file_write(path, strings):
    file_handle = open(path, mode='w')
    file_handle.write(strings)
    file_handle.close()


def get_size(path):
    size = 0
    for root, dirs, files in os.walk(path):
        size += sum([int(os.path.getsize(os.path.join(root, name)) / 1024) for name in files])
    return size


def dist(name):
    url = conf['dist'][name]['url']
    if str(url).count('%s') == 1:
        url = url % ver_conf[name]
    file_name = os.path.basename(url)
    if file_name.count('.') != 0:
        file_name = name + '.' + file_name.split('.', maxsplit=1)[1]
    download_file(url, file_name)
    if 'build_command' in conf['dist'][name].keys():
        run_build_command(name)
        return
    if 'expand' in conf['dist'][name].keys():
        out_path = expand_file(list(conf['dist'][name]['expand'].keys()), name, file_name)
    else:
        out_path = 'tmp/' + file_name

    if 'program_name' in conf['dist'][name]['path'].keys():
        program_name = conf['dist'][name]['path']['program_name']
        check_dir('deb/usr/local/bin')
        os.rename(out_path, 'deb/usr/local/bin/' + program_name)

    if 'config_name' in conf['dist'][name]['path'].keys():
        check_dir('deb/usr/local/etc/')
        shutil.copytree('files/config/' + name, 'deb/usr/local/etc/' + name)

    if 'service_file' in conf['dist'][name]['path'].keys():
        service_name = conf['dist'][name]['path']['service_file']
        check_dir('deb/etc/systemd/system')
        shutil.copyfile('files/servicefiles/' + service_name, 'deb/etc/systemd/system/' + service_name)

    if 'data_path' in conf['dist'][name]['path'].keys():
        data_path = conf['dist'][name]['path']['data_path']
        data_dir = 'deb' + os.path.dirname(str(data_path))
        check_dir(data_dir)
        os.rename('tmp/' + file_name, 'deb' + data_path)


def gen_debfile(name):
    check_enable = []
    mask = []
    unmask = []
    purge = []
    try_restart = []
    stop = []
    custom = ''
    ver = ''
    conffile = ''
    check_dir('deb/DEBIAN')
    size = get_size('deb/')
    deb_name = conf['deb'][name]['name']
    deb_arch = conf['deb'][name]['arch']
    deb_description = conf['deb'][name]['description']

    if 'postinit' in conf['deb'][name].keys():
        deb_custom = conf['deb'][name]['postinit']
        f = open('files/' + deb_custom, 'r')
        for i in f.readlines():
            custom += i
        f.close()

    for i in conf['deb'][name]['main_program']:
        check_enable.append('''\
  if deb-systemd-helper --quiet was-enabled %s.service; then
    deb-systemd-helper enable %s.service > /dev/null || true
    deb-systemd-invoke start %s.service > /dev/null || true
  else
    deb-systemd-helper update-state %s.service > /dev/null || true
  fi''' % (i, i, i, i))
        mask.append('deb-systemd-helper mask %s.service > /dev/null || true' % i)
        unmask.append('deb-systemd-helper unmask %s.service > /dev/null || true' % i)
        purge.append('deb-systemd-helper purge %s.service > /dev/null || true' % i)
        try_restart.append('deb-systemd-invoke try-restart %s.service > /dev/null || true' % i)
        stop.append('deb-systemd-invoke stop %s.service > /dev/null || true' % i)
        ver += ver_conf[i] + '+'
        if 'config_name' in conf['dist'][i]['path'].keys():
            conffile += '/usr/local/etc/' + i + '/' + conf['dist'][i]['path']['config_name'] + '\n'
        if 'config_path' in conf['dist'][i]['path'].keys():
            conffile += conf['dist'][i]['path']['config_path'] + '\n'

    str_control = '''Package: %s
Version: %s
Section:
Priority:
Architecture: %s
Maintainer: zz
Installed-Size: %s
Description: %s
''' % (deb_name, ver.rstrip('+'), deb_arch, size, deb_description)
    file_write('deb/DEBIAN/control', str_control)

    str_postinst = '''#!/bin/sh
set -e
%s
if [ "$1" = "configure" ] || [ "$1" = "abort-upgrade" ] || [ "$1" = "abort-deconfigure" ] || [ "$1" = "abort-remove" ]; then
%s
%s
  if [ -d /run/systemd/system ]; then
    systemctl --system daemon-reload > /dev/null || true
    if [ -n "$2" ]; then
%s
    fi
  fi
fi''' % (custom, add_space(unmask,2), add_space(check_enable,0), add_space(try_restart,6))
    file_write('deb/DEBIAN/postinst', str_postinst)

    str_postrm = '''#!/bin/sh
set -e
if [ -d /run/systemd/system ]; then
  systemctl --system daemon-reload > /dev/null || true
fi
if [ "$1" = "remove" ]; then
  if [ -x "/usr/bin/deb-systemd-helper" ]; then
%s
  fi
fi
if [ "$1" = "purge" ]; then
  if [ -x "/usr/bin/deb-systemd-helper" ]; then
%s
%s
  fi
fi''' % (add_space(mask,4), add_space(purge,4), add_space(unmask,4))
    file_write('deb/DEBIAN/postrm', str_postrm)

    str_prerm = '''#!/bin/sh
set -e
if [ -d /run/systemd/system ] && [ "$1" = remove ]; then
%s
fi''' % add_space(stop,2)
    file_write('deb/DEBIAN/prerm', str_prerm)

    str_conffiles = '''%s''' % conffile
    file_write('deb/DEBIAN/conffiles', str_conffiles)

    os.chmod('deb/DEBIAN/postinst', 0o755)
    os.chmod('deb/DEBIAN/postrm', 0o755)
    os.chmod('deb/DEBIAN/prerm', 0o755)


def main(name):
    os.mkdir('tmp')
    os.mkdir('deb')
    for i in conf['deb'][name]['include']:
        dist(i)
    os.mkdir('tmp/DEBIAN')
    gen_debfile(name)
    deb_name = conf['deb'][name]['name']
    os.system('dpkg-deb -b deb/ ' + deb_name + '.deb')
    shutil.rmtree('tmp')
    shutil.rmtree('deb')
    if update_flag == 1:
        os.system('''cat version.json | tr -d '",{}' | grep -v "^$" > version''')
        os.system('git config --local user.name "github-actions[bot]"')
        os.system('git config --local user.email "41898282+github-actions[bot]@users.noreply.github.com"')
        os.system('git add .')
        os.system('git commit -am ' + commit)
        os.system('git push')

if __name__ == "__main__":
    n = 0
    for num in conf['deb']:
        check_version(num['main_program'], n)
        n = n + 1
