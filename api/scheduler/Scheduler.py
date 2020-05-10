
import logging
logger = logging.getLogger('api')
from apscheduler.schedulers.background import BackgroundScheduler

from api.Config import config
from api.voip.axl import axl_clusters 
from api.voip.serviceability import serviceability_clusters
from api.crud import settings_management

# background task functions

def scheduler_phone_sync(manual: bool = False):
  """Triggers CUCM API sync to poll phone data from CUCM clusters

  This will trigger an update against all CUCM clusters configured in the DB

  Keyword Arguments:
      manual {bool} -- Specifies whether this was manually triggered (True) or triggered via APSchedulers (False) (default: {False})

  """

  scheduler.pause()  # stop scheduler because multiple tasks can cause problems with DB writes
  
  if manual:
    trigger_method = "manual"
  else:
    trigger_method = "scheduled"

  logger.info(f'APscheduler {trigger_method} cucm phone sync triggered')

  from api.scheduler import update_from_cucm
  
  # loop through CUCM clusters
  for cluster in axl_clusters.clusters:

    # Call actual CUCM update script
    update_from_cucm.update_cucm(
      axl_ucm= axl_clusters.get_cluster(cluster_name=cluster), 
      serviceability_ucm= serviceability_clusters.get_cluster(cluster_name=cluster), 
      cluster_name=cluster
    )

  scheduler.resume() # resume scheduler

def scheduler_phonescrape_sync(manual: bool = False):
  """Triggers Phone scrape sync to query all IP phone web servers to scrape data into DB

  Keyword Arguments:
      manual {bool} -- Specifies whether this was manually triggered (True) or triggered via APSchedulers (False) (default: {False})
  """
  scheduler.pause() # stop scheduler because multiple tasks can cause problems with DB writes

  if manual:
    trigger_method = "manual"
  else:
    trigger_method = "scheduled"

  logger.info(f'APscheduler {trigger_method} phonescrape update triggered')

  from api.scheduler.update_from_phonescraper import rq_scrape_phones

  # call phone scrape script to do the actual work
  rq_scrape_phones()

  scheduler.resume() # resume scheduler

# scheduler init
scheduler = BackgroundScheduler()

# get settings values from database and convert values to dict
settings = settings_management.get_all_settings()
settings_dict = {}
for setting in settings:
  settings_dict[setting.name] = setting.value

# schedule CUCM API phone sync job
scheduler_phone_sync_job = scheduler.add_job(scheduler_phone_sync, 'cron', hour='*', minute=settings_dict['cucm_update_minute'])

# schedule Phonescrape API sync job
scheduler_phonescrape_sync_job = scheduler.add_job(scheduler_phonescrape_sync, 'cron', hour=settings_dict['phonescrape_update_time'].split(':')[0], minute=settings_dict['phonescrape_update_time'].split(':')[1])
  

def reschedule_jobs():
  """Reschedules CUCM/Phone scrape jobs with updated schedule/times
  Used when a user manually changes the scheduler time in the application
  """

  logger.info("rescheduling jobs..")
  # get times from settings
  settings = settings_management.get_all_settings()

  settings_dict = {}

  for setting in settings:
    settings_dict[setting.name] = setting.value

  # Reschedule CUCM API phone sync job
  scheduler_phone_sync_job.reschedule(trigger='cron', hour='*', minute=settings_dict['cucm_update_minute'])

  # Reschedule Phonescrape API sync job
  scheduler_phonescrape_sync_job.reschedule(trigger='cron', hour=settings_dict['phonescrape_update_time'].split(':')[0], minute=settings_dict['phonescrape_update_time'].split(':')[1])

