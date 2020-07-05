import logging
import traceback
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .objects import Experience, Education, Scraper, Interest, Accomplishment
import os

_logger = logging.getLogger("LinkedinScraper-Person")


class Person(Scraper):

    __TOP_CARD = "pv-top-card"

    def __init__(self, linkedin_url=None, name=None, experiences=None,  # NOQA
                 educations=None, interests=None, accomplishments=None,
                 driver=None, get=True, scrape=True, close_on_complete=True):
        self.linkedin_url = linkedin_url
        self.name = name
        if experiences is None:
            experiences = []
        self.experiences = experiences
        if educations is None:
            educations = []
        self.educations = educations
        if interests is None:
            interests = []
        self.interests = interests
        if accomplishments is None:
            accomplishments = []
        self.accomplishments = accomplishments
        self.also_viewed_urls = []

        if driver is None:
            try:
                if os.getenv("CHROMEDRIVER") is None:
                    driver_path = os.path.join(os.path.dirname(
                        __file__), 'drivers/chromedriver')
                else:
                    driver_path = os.getenv("CHROMEDRIVER")

                driver = webdriver.Chrome(driver_path)
            except Exception:
                _logger.error(traceback.format_exc())
                driver = webdriver.Chrome()

        if get:
            driver.get(linkedin_url)

        self.driver = driver

        if scrape:
            self.scrape(close_on_complete)

    def add_experience(self, experience):
        self.experiences.append(experience)

    def add_education(self, education):
        self.educations.append(education)

    def add_interest(self, interest):
        self.interests.append(interest)

    def add_accomplishment(self, accomplishment):
        self.accomplishments.append(accomplishment)

    def add_location(self, location):
        self.location = location

    def scrape(self, close_on_complete=True):

        if self.is_signed_in():
            self.scrape_logged_in(close_on_complete=close_on_complete)
        else:
            print('you are not logged in!')
            _ = input(
                'please verify the capcha then press any key to continue...')
            self.scrape_not_logged_in(close_on_complete=close_on_complete)

    def scrape_logged_in(self, close_on_complete=True):  # NOQA
        driver = self.driver
        duration = None

        root = driver.find_element_by_class_name(self.__TOP_CARD)
        self.name = root.find_elements_by_xpath(
            "//section/div/div/div/*/li")[0].text.strip()

        driver.execute_script(
            "window.scrollTo(0, Math.ceil(document.body.scrollHeight/2));")

        # get experience
        try:
            _ = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, "experience-section")))
            exp = driver.find_element_by_id("experience-section")
        except Exception:
            _logger.error(traceback.format_exc())
            exp = None

        if (exp is not None):
            for position in exp.find_elements_by_class_name(
                    "pv-position-entity"):
                position_title = position.find_element_by_tag_name(
                    "h3").text.encode('utf-8').strip()

                try:
                    company = position.find_elements_by_tag_name(
                        "p")[1].text.encode('utf-8').strip()
                    times = str(
                        position.find_elements_by_tag_name(
                            "h4")[0].find_elements_by_tag_name(
                            "span")[1].text.strip()
                    )
                    from_date = " ".join(times.split(' ')[:2])
                    to_date = " ".join(times.split(' ')[3:])
                    duration = position.find_elements_by_tag_name(
                        "h4")[1].find_elements_by_tag_name(
                        "span")[1].text.strip()
                    location = position.find_elements_by_tag_name(
                        "h4")[2].find_elements_by_tag_name(
                        "span")[1].text.strip()
                except Exception:
                    _logger.error(traceback.format_exc())
                    company = None
                    from_date, to_date, duration, location = (
                        None, None, None, None)

                experience = Experience(
                    position_title=position_title,
                    from_date=from_date,
                    to_date=to_date,
                    duration=duration,
                    location=location
                )
                experience.institution_name = company
                self.add_experience(experience)

        # get location
        location = driver.find_element_by_class_name(
            f'{self.__TOP_CARD}--list-bullet')
        location = location.find_element_by_tag_name('li').text
        self.add_location(location)

        driver.execute_script(
            "window.scrollTo(0, Math.ceil(document.body.scrollHeight/1.5));")

        # get education
        try:
            _ = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, "education-section")))
            edu = driver.find_element_by_id("education-section")
        except Exception:
            _logger.error(traceback.format_exc())
            edu = None

        if (edu is not None):
            for school in edu.find_elements_by_class_name("pv-profile-section__list-item"):  # NOQA
                university = school.find_element_by_class_name(
                    "pv-entity__school-name").text.encode('utf-8').strip()

                try:
                    degree = school.find_element_by_class_name(
                        "pv-entity__degree-name").find_elements_by_tag_name(
                        "span")[1].text.encode('utf-8').strip()
                    times = school.find_element_by_class_name(
                        "pv-entity__dates").find_elements_by_tag_name(
                        "span")[1].text.strip()
                    from_date, to_date = (times.split(
                        " ")[0], times.split(" ")[2])
                except Exception:
                    _logger.error(traceback.format_exc())
                    degree = None
                    from_date, to_date = (None, None)
                education = Education(
                    from_date=from_date, to_date=to_date, degree=degree)
                education.institution_name = university
                self.add_education(education)

        # get interest
        try:
            _ = WebDriverWait(driver, 3).until(EC.presence_of_element_located(
                (By.XPATH, "//*[@class='pv-profile-section pv-interests-section artdeco-container-card ember-view']")))  # NOQA
            interestContainer = driver.find_element_by_xpath(
                "//*[@class='pv-profile-section pv-interests-section artdeco-container-card ember-view']")  # NOQA
            for interestElement in interestContainer.find_elements_by_xpath("//*[@class='pv-entity__summary-info ember-view']"):   # NOQA
                interest = Interest(interestElement.find_element_by_tag_name(
                    "h3").text.encode('utf-8').strip())
                self.add_interest(interest)
        except Exception:
            _logger.error(traceback.format_exc())
            pass

        # get accomplishment
        try:
            _ = WebDriverWait(driver, 3).until(EC.presence_of_element_located(
                (By.XPATH, "//*[@class='pv-profile-section pv-accomplishments-section artdeco-container-card ember-view']")))  # NOQA
            acc = driver.find_element_by_xpath(
                "//*[@class='pv-profile-section pv-accomplishments-section artdeco-container-card ember-view']")  # NOQA
            for block in acc.find_elements_by_xpath("//div[@class='pv-accomplishments-block__content break-words']"):  # NOQA
                category = block.find_element_by_tag_name("h3")
                for title in block.find_element_by_tag_name("ul").find_elements_by_tag_name("li"):  # NOQA
                    accomplishment = Accomplishment(category.text, title.text)
                    self.add_accomplishment(accomplishment)
        except Exception:
            _logger.error(traceback.format_exc())
            pass

        if close_on_complete:
            driver.quit()

    def scrape_not_logged_in(self, close_on_complete=True, retry_limit=10):  # NOQA
        driver = self.driver
        retry_times = 0
        while self.is_signed_in() and retry_times <= retry_limit:
            _ = driver.get(self.linkedin_url)
            retry_times = retry_times + 1

        # get name
        self.name = driver.find_element_by_class_name(
            "top-card-layout__title").text.strip()

        # get experience
        try:
            _ = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, "experience")))
            exp = driver.find_element_by_class_name("experience")
        except Exception:
            _logger.error(traceback.format_exc())
            exp = None

        if exp is not None:
            for position in exp.find_elements_by_class_name("experience-item__contents"):  # NOQA
                position_title = position.find_element_by_class_name(
                    "experience-item__title").text.strip()
                company = position.find_element_by_class_name(
                    "experience-item__subtitle").text.strip()

                try:
                    times = position.find_element_by_class_name(
                        "experience-item__duration")
                    from_date = times.find_element_by_class_name(
                        "date-range__start-date").text.strip()
                    try:
                        to_date = times.find_element_by_class_name(
                            "date-range__end-date").text.strip()
                    except Exception:
                        _logger.error(traceback.format_exc())
                        to_date = "Present"
                    duration = position.find_element_by_class_name(
                        "date-range__duration").text.strip()
                    location = position.find_element_by_class_name(
                        "experience-item__location").text.strip()
                except Exception:
                    _logger.error(traceback.format_exc())
                    from_date, to_date, duration, location = (
                        None, None, None, None)

                experience = Experience(
                    position_title=position_title,
                    from_date=from_date,
                    to_date=to_date,
                    duration=duration,
                    location=location
                )
                experience.institution_name = company
                self.add_experience(experience)
        driver.execute_script(
            "window.scrollTo(0, Math.ceil(document.body.scrollHeight/1.5));")

        # get education
        edu = driver.find_element_by_class_name("education__list")
        for school in edu.find_elements_by_class_name("result-card"):
            university = school.find_element_by_class_name(
                "result-card__title").text.strip()
            degree = school.find_element_by_class_name(
                "education__item--degree-info").text.strip()
            try:
                times = school.find_element_by_class_name("date-range")
                from_date = times.find_element_by_class_name(
                    "date-range__start-date").text.strip()
                to_date = times.find_element_by_class_name(
                    "date-range__end-date").text.strip()
            except Exception:
                _logger.error(traceback.format_exc())
                from_date, to_date = (None, None)
            education = Education(from_date=from_date,
                                  to_date=to_date, degree=degree)
            education.institution_name = university
            self.add_education(education)

        if close_on_complete:
            driver.close()

    def __repr__(self):
        return (
            "{name}\n\n"
            "Experience\n{exp}\n\n"
            "Education\n{edu}\n\n"
            "Interest\n{int}\n\n"
            "Accomplishments\n{acc}"
        ).format(
            name=self.name,
            exp=self.experiences,
            edu=self.educations,
            int=self.interests,
            acc=self.accomplishments)
