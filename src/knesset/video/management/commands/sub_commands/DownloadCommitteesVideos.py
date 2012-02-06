# encoding: utf-8

import os, sys, traceback
from knesset.video.management.commands.sub_commands import SubCommand
from django.contrib.contenttypes.models import ContentType
from knesset.committees.models import Committee
from knesset.video.models import Video
import knesset.video.utils.mms as utils_mms
from knesset.video.utils import get_videos_queryset

class DownloadCommitteesVideos(SubCommand):
	
	def __init__(self,command,mms=None,mb_quota=None):
		if mms is None: mms=utils_mms
		SubCommand.__init__(self,command)
		self._verifyDataDir()
		videos=self._getVideosToDownload()
		self._debug('got '+str(len(videos))+' videos from db that needs to be downloaded')
		total_bytes=0
		for video in videos:
			if mb_quota is not None and (total_bytes/1000000)>mb_quota:
				self._warn('reached mb quota of '+str(mb_quota)+'mb')
				break
			self._check_timer()
			url=video.embed_link
			self._debug('downloading video - '+url)
			filename=self._get_data_root()+'committee_mms_videos/'+self._getFilenameFromUrl(url)			
			if self._isAlreadyDownloaded(filename):
				self._debug("file already downloaded: "+filename)
				total_bytes=total_bytes+self._getFileSize(filename)
				continue
			else:
				partfilename=filename+'.part'
				try:
					streamsize=mms.get_size(url)
				except Exception, e:
					self._warn('failed to get mms stream size, exception = '+str(e))
					traceback.print_exc(file=sys.stdout)
				else:
					self._debug('got mms stream size = '+str(streamsize))
					mins_remaining=round(self._timer_remaining()/60)
					downloaded=False
					if self._isAlreadyDownloaded(partfilename):
						filesize=self._getFileSize(partfilename)
						if filesize<streamsize:
							self._debug('resuming download')
							try:
								isDownloadDone=mms.resume_download(url,partfilename,mins_remaining)
								downloaded=True
							except Exception, e:
								self._warn('failed to resume mms download, exception = '+str(e))
								traceback.print_exc(file=sys.stdout)
					else:
						self._debug('starting new download')
						try:
							isDownloadDone=mms.download(url,partfilename,mins_remaining)
							downloaded=True
						except Exception, e:
							self._warn('failed to resume mms download, exception = '+str(e))
							traceback.print_exc(file=sys.stdout)
					if downloaded:
						self._check_timer()
						filesize=self._getDownloadedFileSize(partfilename)
						self._debug('downloaded file size: '+str(filesize))
						if isDownloadDone:
							self._renameFile(partfilename,filename)
							self._debug("finished downloading: "+filename)
						total_bytes=total_bytes+filesize

	def _verifyDataDir(self):
		if not os.path.exists(self._get_data_root()+'committee_mms_videos'):
			os.makedirs(self._get_data_root()+'committee_mms_videos')

	def _getFilenameFromUrl(self,url):
		filename=url.split('/')
		filename=filename[len(filename)-1]
		return filename

	def _getVideosToDownload(self):
		ret=[]
		object_type=ContentType.objects.get_for_model(Committee)
		videos=Video.objects.filter(content_type__pk=object_type.id,group='mms').order_by('id')
		for video in videos:
			qs=get_videos_queryset(video,group='youtube_upload',ignoreHide=True)
			if qs.count()==0:
				ret.append(video)
		return ret
	
	def _isAlreadyDownloaded(self,filename):
		return os.path.exists(filename)
	
	def _getFileSize(self,filename):
		return os.path.getsize(filename)
	
	def _getDownloadedFileSize(self,filename):
		return self._getFileSize(filename)
	
	def _renameFile(self,filename,newfilename):
		os.rename(filename,newfilename)

