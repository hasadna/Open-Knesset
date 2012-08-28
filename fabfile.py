from fabric.api import run, env, cd, sudo, roles, runs_once

# add a local_fab_settings.py file,
# so that you can access your servers
# but please, don't commit it to git.
try: 
    from local_fab_settings import *
except ImportError as e:
    pass

# web server stuff
def web_apache_cmd(cmd):
	if cmd not in ['start','stop','restart']:
		raise Exception('Unknown apache command %s' % cmd)
	sudo('/etc/init.d/apache2 %s' % cmd)

def _update_commit():
	with cd("/oknesset_web/Open-Knesset"):
		sudo('git log --pretty=format:"Code Commit: %H <br>Last Update: %cd" -n 1 > src/knesset/templates/last_build.txt',
			user='oknesset')

def _chown(to_user,directory='Open-Knesset'):
	sudo("chown -R %s %s" % (to_user,directory))

@roles('web')
def deploy_web(buildout=False):
	web_apache_cmd('stop')
	with cd('/oknesset_web'):
		_chown('oknesset')
		with cd('Open-Knesset'):
			_git_pull()
			if buildout:
				_run_buildout()
			_update_commit()
		_chown('www-data')
	web_apache_cmd('start')

# db server stuff - should only run once on master db!
@runs_once
def db_migrate_syncdb():
	with cd("/oknesset_data/Open-Knesset"):
		run("bin/django syncdb --migrate")

@roles('db')
def deploy_backend(migration=False,buildout=False):
	with cd("/oknesset_data/Open-Knesset"):
		_git_pull()
		if buildout:
			_run_buildout()
		if migration:
			db_migrate_syncdb()

@roles('db_master')
def show_cron(as_user='oknesset'):
	sudo('crontab -l',user=as_user)

@roles('db')
def db_show_replication():
	# works on both servers
	run('ps -ef | grep postgres | grep -e receiver -e sender')

# memcache commands
@roles('memcache')
def mc_flushall():
	run('echo flush_all | telnet localhost 11211')

# commands for all servers
def _git_pull(repo='origin', branch='master',as_user='oknesset'):
	sudo("git pull %s %s" % (repo,branch),user=as_user)

def _run_buildout():
	sudo('bin/buildout',user='oknesset')

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

def deploy_all(repo='origin', branch='master',use_buildout=False,use_migration=False,reset_memcache=False):
    deploy_backend(buildout=use_buildout,migration=use_migration)
    deploy_web(buildout=use_buildout)
    if reset_memcache:
    	mc_flushall()	