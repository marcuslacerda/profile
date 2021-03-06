"""People class."""
import logging
import requests
import urlparse
import json
from requests.auth import HTTPBasicAuth
from lxml import html
import re
import datetime

logger = logging.getLogger('profile')


class People(object):
    """Class to manage all operations of people.

    This class expect a config like this:
    people.user and people.pass can be override using environment variables
    config.get('PEOPLE_PEOPLE_USER')

    p = People(config)
    """

    def __init__(self, config):
        """Initialize People client API."""
        self.config = config
        self.people_host = config.get('PEOPLE_PEOPLE_HOST')
        self.username = config.get('PEOPLE_PEOPLE_USER')
        self.password = config.get('PEOPLE_PEOPLE_PASS')

    def get_profile_page_by_user(self, login):
        """Scan project name from people system using login as parameter.

        Args:
              login: Username for build url https://people.cit.com.br/profile/+login
        """
        url = '%s/profile/%s' % (self.people_host, login)
        response = requests.get(url=url, auth=HTTPBasicAuth(self.username, self.password))
        # logger.debug('user %s and pass %s' % (self.username, self.password))

        # Response
        # print response.status_code
        logger.debug(url)
        logger.debug(response.status_code)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            logger.error("fail to load project name for %s. Check people username and password" % login)
            return None

        return html.fromstring(response.text)


    def scan_project(self, parsed_body):
        """Scan project name from people system using parsed_body html.

        Args:
              parsed_body: html page load for build url https://people.cit.com.br/profile/+login
        """
        elements =  parsed_body.xpath('.//div[@class="user-projects"]//ul//li[1]//a')

        if elements:
            return elements[0].text_content()
        else:
            logger.warning('Project name not found')
            return 'Empty'

    def scan_awards(self, parsed_body):
        """Get awards from people system using parsed_body html.

        Args:
              parsed_body: html page load from https://people.cit.com.br/profile/+login
        """
        elements =  parsed_body.xpath('.//div[@class="user-awards"]//div[@class="icon-container"]//img')

        awards = []

        for element in elements:
            title = element.get('title')

            award_fields = title.split(' | ')

            # print award_fields[0]

            doc_award = {
                'name': award_fields[0].strip()
            }
            if len(award_fields) > 2:
                doc_award['description'] = award_fields[1]

            for field in award_fields:
                m = re.search(r'(\d+-\d+-\d+)', field)
                if  m:
                    given_at = datetime.datetime.strptime(m.group(1), '%d-%m-%y')
                    doc_award['given_at'] = given_at

                if 'Given by' in field:
                    doc_award['given_by'] = field.split('Given by')[1]


            if 'given_at' not in doc_award:
                doc_award['given_at'] = datetime.datetime.strptime('01-01-00', '%d-%m-%y')
            awards.append(doc_award)

        logger.debug('%s awards', len(awards))
        awards.sort(key=lambda x: x['given_at'], reverse=True)

        return awards


    def find_user_by_login(self, login):
        """Find user by login.

        Args:
              login: Username for build url https://people.cit.com.br/search/json?q=login:{login}
        """
        url = '%s/search/json?q=login:%s' % (self.people_host, login)
        response = requests.get(url=url, auth=HTTPBasicAuth(self.username, self.password))

        # Response
        logger.debug(url)
        logger.debug(response.status_code)
        if response.status_code != 200:
            logger.error("fail to load project name for %s. Check people username and password" % login)
            return None

        json_data = json.loads(response.text)

        print json_data

        if json_data['data']:
            return json_data['data'][0]
        else:
            return None

    def find_coach_by_login(self, login):
        """Find coach by login."""
        people = self.find_user_by_login(login)

        if not people:
            logger.warning("people %s was not found" % login)
            return None

        # index 5 is a coach login
        coach = people[5]
        if not coach:
            logger.warning("%s has no coach" % login)
            return None

        return self.find_user_by_login(coach)


    def find_pdm_by_login(self, login):
        """Find pdm by login."""
        people = self.find_user_by_login(login)

        if not people:
            logger.warning("people %s was not found" % login)
            return None

        # index 6 is a pdm login
        pdm = people[6]
        if not pdm:
            logger.warning("%s has no pdm" % login)
            return None

        return self.find_user_by_login(pdm)

    def find_all_users(self):
        """Return all ative users from people system.

        Needs config['PEOPLE_GATEWAY_APP_TOKEN'] to call people URL. app_token:
        it is a token form api gateway. You need to request one for you
        if you want call this API.
        """
        token = self.config.get('PEOPLE_GATEWAY_APP_TOKEN')
        headers = {'app_token': token}

        url = '%s/cit/api/v2/people' % self.config.get('PEOPLE_GATEWAY_HOST')

        logger.debug('Retreive all users')
        logger.debug('url = %s' %url)
        response = requests.get(url=url, headers=headers)

        logger.info('status %s' % response.status_code)

        return response.json()

    def find_user(self, login):
        """Return all ative users from people system.

        Needs config['PEOPLE_GATEWAY_APP_TOKEN'] to call people URL. app_token:
        it is a token form api gateway. You need to request one for you
        if you want call this API.
        """
        token = self.config.get('PEOPLE_GATEWAY_APP_TOKEN')
        headers = {'app_token': token}

        url = '%s/cit/api/v2/people/%s' % (self.config.get('PEOPLE_GATEWAY_HOST'), login)

        logger.debug('Retreive user')
        logger.debug('url = %s' %url)
        response = requests.get(url=url, headers=headers)

        logger.info('status %s' % response.status_code)

        return response.status_code, response.json()

    def dumpImage(self, login):
        """Download user's image and save it at 'download_images dir."""
        endpoint_url = '%s/profile/%s' % (self.people_host, login)
        response = requests.get(url=endpoint_url, auth=HTTPBasicAuth(self.username, self.password))

        parsed_body = html.fromstring(response.text)

        # Grab links to all images
        images = parsed_body.xpath('.//div[@class="container"]/div[@class="photo"]/img/@src')

        if images:
            # Convert any relative urls to absolute urls
            images = [urlparse.urljoin(response.url, url) for url in images]
            logger.info('Found %s images' % len(images))

            # Only download first 10
            for url in images[0:10]:
                r = requests.get(url, auth=HTTPBasicAuth(self.username, self.password))
                f = open('downloaded_images/%s' % url.split('/')[-1], 'w')
                f.write(r.content)
                f.close()
