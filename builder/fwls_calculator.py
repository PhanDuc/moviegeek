import os

import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prs_project.settings")

import django
from django.db.models import Count

django.setup()

import pandas as pd
import numpy as np
from sklearn import linear_model

from recs.content_based_recommender import ContentBasedRecs
from recs.neighborhood_based_recommender import NeighborhoodBasedRecs
from analytics.models import Rating
from recs.fwls_recommender import FeatureWeightedLinearStacking

import numpy as np
from sklearn.model_selection import train_test_split

import statsmodels.formula.api as sm


class FWLSCalculator(object):

    def __init__(self, data_size = 1000):
        self.logger = logging.getLogger('FWLS')
        self.train_data = None
        self.test_data = None
        self.rating_count = None
        self.cb = ContentBasedRecs()
        self.cf = NeighborhoodBasedRecs()
        self.fwls = FeatureWeightedLinearStacking()
        self.data_size = data_size

    def get_real_training_data(self):
        columns = ['user_id', 'movie_id', 'rating', 'type']
        ratings_data = Rating.objects.all().values(*columns)[:self.data_size]
        df = pd.DataFrame.from_records(ratings_data, columns=columns)
        self.train_data, self.test_data = train_test_split(df, test_size=0.2)
        self.logger.debug("training data loaded {}".format(len(ratings_data)))

    def calculate_predictions_for_training_data(self):
        self.logger.debug("[BEGIN] getting predictions")

        self.train_data['cb'] = self.train_data.apply(lambda data:
                                            self.cb.predict_score(data['user_id'], data['movie_id']), axis=1)
        self.train_data['cf'] = self.train_data.apply(lambda data:
                                            self.cf.predict_score(data['user_id'], data['movie_id']), axis=1)

        self.logger.debug("[END] getting predictions")
        return None

    def calculate_feature_functions_for_training_data(self):
        self.logger.debug("[BEGIN] calculating functions")
        self.train_data['cb1'] = self.train_data.apply(lambda data:
                                             data['cb'] * self.fwls.fun1(), axis=1)
        self.train_data['cb2'] = self.train_data.apply(lambda data:
                                             data['cb'] * self.fwls.fun2(data['user_id']), axis = 1)

        self.train_data['cf1'] = self.train_data.apply(lambda data:
                                             data['cf'] * self.fwls.fun1(), axis=1)
        self.train_data['cf2'] = self.train_data.apply(lambda data:
                                             data['cf'] * self.fwls.fun2(data['user_id']), axis = 1)

        self.logger.debug("[END] calculating functions")
        return None

    def train(self):
        #model = sm.ols(formula="rating ~ cb1+cb2+cf1+cf2", data=self.train_data[['rating', 'cb1','cb2','cf1','cf2']])
        #results = model.fit()
        #self.logger.info(results.summary())
        #self.logger.info(results.params)
        regr = linear_model.LinearRegression()

        regr.fit(self.train_data[['cb1','cb2','cf1','cf2']], self.train_data['rating'])
        self.logger.info(regr.coef_)
        return regr.coef_


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)
    logger = logging.getLogger('funkSVD')
    logger.info("[BEGIN] Calculating Feature Weighted Linear Stacking...")

    if not os.path.exists("./models/lda/model.lda"):
        logger.error("lda model should be done first. please run the lda_model_calculator.py script")
        exit()

    fwls = FWLSCalculator(data_size=10000)
    fwls.get_real_training_data()
    logger.info(fwls.train_data)

    fwls.calculate_predictions_for_training_data()
    fwls.calculate_feature_functions_for_training_data()
    logger.info("Freatures trained")
    logger.info("[BEGIN] training of FWLS")
    fwls.train()
    logger.info("[END] training of FWLS")
    logger.info("[END] Calculating Feature Weighted Linear Stacking...")
