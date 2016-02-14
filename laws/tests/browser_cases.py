# encoding: utf-8
from datetime import time, datetime

from django.contrib.auth.models import User

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from knesset.browser_test_case import BrowserTestCase, on_platforms
from laws.models import Vote, Bill
from laws.forms import LINK_ERRORS

# All browser test cases must inherit from BrowserTestCase which initializes the selenium framework
# also, they must use the @on_platforms decorator. This decorator can run the test case several times - for different browser and platforms.

@on_platforms()
class VoteViewsBrowserTest(BrowserTestCase):
    """
    Test the Vote views in the browser
    """
    def login(self):
        if hasattr(self, 'logged_in') and self.logged_in is True:
            return

        self.user_name = u'test-user'
        self.user_passwd = u'123456'

        try:
            self.user = User.objects.get(username=self.user_name)
        except:
            # Create new
            self.user = User.objects.create_user(username=self.user_name,
                                                 password=self.user_passwd)

        self.driver.get(self.live_server_url + '/users/login/')
        user_el = self.driver.find_element_by_id('id_username')
        passwd_el = self.driver.find_element_by_id('id_password')
        user_el.send_keys(self.user.username)
        passwd_el.send_keys(self.user_passwd)
        passwd_el.submit()
        self.logged_in = True

    def load_data(self):
        try:
            self.vote_1 = Vote.objects.get(id=self.vote_1.id)
        except:
            self.vote_1 = Vote.objects.create(time=datetime(2001, 9, 11))
            self.vote_1.title = 'Vote 1 - %d' % self.vote_1.id
            self.vote_1.save()

        try:
            self.vote_2 = Vote.objects.get(id=self.vote_2.id)
        except:
            self.vote_2 = Vote.objects.create(time=datetime(2001, 9, 11))
            self.vote_2.title = 'Vote 1 - %d' % self.vote_2.id
            self.vote_2.save()

        try:
            self.bill_1 = Bill.objects.get(id=self.bill_1.id)
        except:
            self.bill_1 = Bill.objects.create(stage='1')
            self.bill_1.title = 'Bill 1 - %d' % self.bill_1.id
            self.bill_1.save()

        try:
            self.bill_2 = Bill.objects.get(id=self.bill_2.id)
        except:
            self.bill_2 = Bill.objects.create(stage='1')
            self.bill_2.title = 'Bill 1 - %d' % self.bill_2.id
            self.bill_2.save()

    def unload_data(self):
        self.vote_1.delete()
        self.vote_2.delete()
        self.bill_1.delete()
        self.bill_2.delete()

    def get_vote_page(self, vote):
        self.driver.get('%s/vote/%s' % (self.live_server_url, vote.id))

        self.vote_model_el = self.driver.find_element_by_id('id_vote_model')
        self.vote_type_el = Select(self.driver.find_element_by_id('id_vote_type'))
        self.bill_model_el = self.driver.find_element_by_id('id_bill_model')
        self.bill_ac_el = self.driver.find_element_by_id('bill_model_ac')

    def link_vote_to_bill(self, vote_type, vote, bill):
        self.login()
        self.get_vote_page(vote)

        self.vote_type_el.select_by_value(vote_type)

        self.bill_ac_el.send_keys(bill.title)
        self.driver.find_element_by_class_name('autocomplete')\
            .find_element_by_css_selector('div:first-child')\
            .click()

        self.bill_ac_el.submit()


    ### TESTS ###
    def test_bill_form_fields_exist(self):
        """ verify form fields exist and vote_model is correct """
        self.login()
        self.load_data()
        self.get_vote_page(self.vote_1)

        # Verify correct vote model is present
        vote_model_id = int(self.vote_model_el.get_attribute('value'))
        self.assertEqual(vote_model_id, self.vote_1.id)
        self.unload_data()

    def test_attach_pre_to_bill(self):
        """ link a vote to a bill as 'prev vote' """
        self.load_data()
        self.link_vote_to_bill('pre vote', self.vote_1, self.bill_1)

        # Verify no errors
        errorlist_els = self.driver\
            .find_elements_by_css_selector('form .errorlist')

        self.assertEqual(len(errorlist_els), 0)

        # Verify bill actualy got the vote attached
        self.load_data()
        self.assertTrue(self.bill_1.pre_votes.filter(id=self.vote_1.id).exists())
        self.unload_data()

    def test_attach_dup_first_to_bill(self):
        """ try to link a first vote to a bill which alreay has one """
        self.load_data()
        # Attach vote_2 as approval vote of bill_1
        self.link_vote_to_bill('first vote', self.vote_2, self.bill_1)

        # Try to link another vote
        self.link_vote_to_bill('first vote', self.vote_1, self.bill_1)

        # Verify there are errors
        errorlist_els = self.driver\
            .find_elements_by_css_selector('form .errorlist')

        self.assertGreater(len(errorlist_els), 0)

        # Verify error text appears
        error = errorlist_els[0].find_element_by_css_selector('li:first-child')
        self.assertEqual(error.text, LINK_ERRORS['DUP_FIRST'])

        self.unload_data()

    def test_attach_dup_approve_to_bill(self):
        """ try to link an approval vote to a bill which alreay has one """
        self.load_data()
        # Attach vote_2 as approval vote of bill_1
        self.link_vote_to_bill('approve vote', self.vote_2, self.bill_1)

        # Try to link another vote
        self.link_vote_to_bill('approve vote', self.vote_1, self.bill_1)

        # Verify there are errors
        errorlist_els = self.driver\
            .find_elements_by_css_selector('form .errorlist')

        self.assertGreater(len(errorlist_els), 0)

        # Verify error text appears
        error = errorlist_els[0].find_element_by_css_selector('li:first-child')
        self.assertEqual(error.text, LINK_ERRORS['DUP_APPROVE'])

        self.unload_data()

    def test_attach_approve_to_two_bills(self):
        """ try to link the same vote to two different bills as approval """
        self.load_data()
        # Attach vote_1 as approval vote of bill_1
        self.link_vote_to_bill('approve vote', self.vote_1, self.bill_1)

        # Try to link to another bill
        self.link_vote_to_bill('approve vote', self.vote_1, self.bill_2)

        # Verify there are errors
        errorlist_els = self.driver\
            .find_elements_by_css_selector('form .errorlist')

        self.assertGreater(len(errorlist_els), 0)

        # Verify error text appears
        error = errorlist_els[0].find_element_by_css_selector('li:first-child')
        self.assertEqual(error.text, LINK_ERRORS['ALREADY_LINKED'])

        self.unload_data()
