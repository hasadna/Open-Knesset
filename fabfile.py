from fabric.api import run, cd, sudo, roles, runs_once, env
from fabric.contrib.files import first

# add a local_fab_settings.py file,
# so that you can access your servers
# but please, don't commit it to git.
try:
    from local_fab_settings import *
except ImportError as e:
    pass


env.venv_roots = ['/oknesset_web/oknesset/', '/oknesset_data/oknesset/']

env.project_dir = 'Open-Knesset'
env.ok_user = 'oknesset'


def _venv_root():
    return first(*env.venv_roots)


def _project_root():
    return _venv_root() + env.project_dir


def _activate():
    return 'source ' + _venv_root() + 'bin/activate'


def virtualenv(command):
    with cd(_project_root()):
        sudo("export HOME=/home/" + env.ok_user + " && " + _activate() + ' && ' + command, user=env.ok_user)


# web server stuff
def web_apache_cmd(cmd):
    if cmd not in ['start', 'stop', 'restart']:
        raise Exception('Unknown apache command %s' % cmd)
    sudo('/etc/init.d/apache2 %s' % cmd)


def restart_oknesset():
    sudo('supervisorctl restart oknesset')


def _update_commit():
    with cd(_project_root()):
        sudo(
            'git log --pretty=format:"Code Commit: %H <br>Last Update: %cd" -n 1 > templates/last_build.txt',
            user=env.ok_user)


def _chown(to_user, directory=env.project_dir):
    sudo("chown -R %s %s" % (to_user, directory))


@roles('web')
def deploy_web(requirements=False):
    web_apache_cmd('stop')
    with cd(_venv_root()):
        _chown(env.ok_user)
        with cd(env.project_dir):
            _git_pull()
            if requirements:
                _install_requirements()
            virtualenv('./manage.py collectstatic --noinput')
            _update_commit()
        #_chown('www-data')
    restart_oknesset()
    web_apache_cmd('start')


# db server stuff - should only run once on master db!
@runs_once
def db_migrate_syncdb():
    virtualenv('./manage.py migrate')


@roles('db')
def deploy_backend(migration=False, requirements=False):
    with cd(_project_root()):
        _git_pull()
        if requirements:
            _install_requirements()
        if migration:
            db_migrate_syncdb()


@roles('db_master')
def show_cron(as_user=env.ok_user):
    sudo('crontab -l', user=as_user)


@roles('db')
def db_show_replication():
    # works on both servers
    run('ps -ef | grep postgres | grep -e receiver -e sender')

# memcache commands


@roles('web')
@runs_once
def mc_flushall():
    #run('echo flush_all | telnet localhost 11211')
    virtualenv(
        "DJANGO_SETTINGS_MODULE='knesset.settings' " +
        "python -c 'from django.core.cache import cache; cache.clear()'"
    )

# commands for all servers


def _git_pull(repo='origin', branch='master', as_user=env.ok_user):
    sudo("git pull %s %s" % (repo, branch), user=as_user)


def _install_requirements():
    virtualenv(
        'cd .. && pip install -r ' +
        env.project_dir + '/requirements.txt && cd ' + _project_root())

@roles('all')
def all_upgrade_system():
    sudo('apt-get update')
    sudo('apt-get upgrade')


@roles('all')
def show_updates():
    sudo('cat /var/lib/update-notifier/updates-available')
    sudo('/usr/lib/update-notifier/update-motd-reboot-required')


@roles('all')
def all_run_cmd(cmd):
    run(cmd)


@roles('all')
def all_sudo_cmd(cmd):
    sudo(cmd)


def deploy_all(repo='origin', branch='master', install_requirements=False, use_migration=False, reset_memcache=False):
    deploy_backend(requirements=install_requirements, migration=use_migration)
    deploy_web(requirements=install_requirements)
    if reset_memcache:
        mc_flushall()
