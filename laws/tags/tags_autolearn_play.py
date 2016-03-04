import numpy as np
# print(__doc__)
# 
# import numpy as np
# import matplotlib.pyplot as plt
#
# from sklearn.datasets import make_multilabel_classification
# from sklearn.multiclass import OneVsRestClassifier
# from sklearn.svm import SVC
# from sklearn.preprocessing import LabelBinarizer
# from sklearn.decomposition import PCA
# from sklearn.cross_decomposition import CCA


def plot_hyperplane(clf, min_x, max_x, linestyle, label):
    # get the separating hyperplane
    w = clf.coef_[0]
    a = -w[0] / w[1]
    xx = np.linspace(min_x - 5, max_x + 5)  # make sure the line is long enough
    yy = a * xx - (clf.intercept_[0]) / w[1]
    plt.plot(xx, yy, linestyle, label=label)


def plot_subfigure(X, Y, subplot, title, transform):
    if transform == "pca":
        X = PCA(n_components=2).fit_transform(X)
    elif transform == "cca":
        X = CCA(n_components=2).fit(X, Y).transform(X)
    else:
        raise ValueError

    min_x = np.min(X[:, 0])
    max_x = np.max(X[:, 0])

    min_y = np.min(X[:, 1])
    max_y = np.max(X[:, 1])

    classif = OneVsRestClassifier(SVC(kernel='linear'))
    classif.fit(X, Y)

    plt.subplot(2, 2, subplot)
    plt.title(title)

    zero_class = np.where(Y[:, 0])
    one_class = np.where(Y[:, 1])
    plt.scatter(X[:, 0], X[:, 1], s=40, c='gray')
    plt.scatter(X[zero_class, 0], X[zero_class, 1], s=160, edgecolors='b',
               facecolors='none', linewidths=2, label='Class 1')
    plt.scatter(X[one_class, 0], X[one_class, 1], s=80, edgecolors='orange',
               facecolors='none', linewidths=2, label='Class 2')

    plot_hyperplane(classif.estimators_[0], min_x, max_x, 'k--',
                    'Boundary\nfor class 1')
    plot_hyperplane(classif.estimators_[1], min_x, max_x, 'k-.',
                    'Boundary\nfor class 2')
    plt.xticks(())
    plt.yticks(())

    plt.xlim(min_x - .5 * max_x, max_x + .5 * max_x)
    plt.ylim(min_y - .5 * max_y, max_y + .5 * max_y)
    if subplot == 2:
        plt.xlabel('First principal component')
        plt.ylabel('Second principal component')
        plt.legend(loc="upper left")




import numpy
import cPickle as pickle
import sys

print >>sys.stderr, 'loading data'; sys.stderr.flush()
keywords, data = pickle.load(open('histograms_with_tags.pkl', 'rb'))
keywords = sorted(list(keywords))

tags = numpy.array([a['tags'] for a in data])
ids = [a['id'] for a in data]
print >>sys.stderr, 'preparing examples'; sys.stderr.flush()
keyword_dict = {}
for i,w in enumerate(keywords):
	keyword_dict[w] = i

learn_data = numpy.zeros((len(data), len(keywords)))
for i,a in enumerate(data):
	histogram = learn_data[i]
	for k,v in a['histogram'].iteritems():
		histogram[keyword_dict[k]] = v

#

print >>sys.stderr, 'vectorizing labels'; sys.stderr.flush()

try:
    from sklearn.preprocessing import MultiLabelBinarizer
    lb = MultiLabelBinarizer()
except ImportError, e:
    from sklearn.preprocessing import LabelBinarizer
    lb = LabelBinarizer()


TRIM_SAMPLES = len(tags) #/ 10
tags = tags[:TRIM_SAMPLES]
learn_data = learn_data[:TRIM_SAMPLES]

lb.fit(tags)
labels = lb.transform(tags)

print "using\t",TRIM_SAMPLES,"samples"
print "\t",len(keywords),"keywords"
print "\t",len(lb.classes_),"tags"
metadata = learn_data.sum(axis=1)

print "\t",metadata.mean(), "avg words in document"
print "\t",metadata.max(), "biggest document"
print "\t",metadata.min(), "smallest document"


#plt.figure(figsize=(8, 6))
#plot_subfigure(learn_data, labels, 1, "With unlabeled samples + CCA", "cca")
#plot_subfigure(learn_data, labels, 2, "With unlabeled samples + PCA", "pca")
#plt.subplots_adjust(.04, .02, .97, .94, .09, .2)
#plt.show()

from sklearn.multiclass import OneVsRestClassifier, OneVsOneClassifier

#from sklearn.utils.validation import check_consistent_length
from sklearn.multiclass import _fit_ovo_binary, check_consistent_length, np, Parallel, delayed
class OneVsOneClassifierMultiLabel(OneVsOneClassifier):

    def fit(self, X, y):
        y = np.asarray(y)
        check_consistent_length(X, y)

        self.classes_ = np.arange(y.shape[1]) + 1
        n_classes = self.classes_.shape[0]
        self.estimators_ = Parallel(n_jobs=self.n_jobs)(
            delayed(_fit_ovo_binary)(
                self.estimator, X, self.classes_[i] * y[:,i] + self.classes_[j] * y[:,j], self.classes_[i], self.classes_[j])
            for i in range(n_classes) for j in range(i + 1, n_classes))

        return self

    def predict(self, X):
        Y = self.decision_function(X)

        return self.classes_[Y.argmax(axis=1)]

    def decision_function(self, X):
        check_is_fitted(self, 'estimators_')
        import pdb; pdb.set_trace()

        n_samples = X.shape[0]
        n_classes = self.classes_.shape[0]
        votes = np.zeros((n_samples, n_classes, n_classes))

        k = 0
        for i in range(n_classes):
            for j in range(i + 1, n_classes):
                pred = self.estimators_[k].predict(X)
                votes[:, i, j] += pred
                k += 1
        return votes

class KoppelSameAuthorClassifier(object):
    def __init__(self):
        super(KoppelSameAuthorClassifier, self).__init__()
        self.class_data = None
        self.orig_data = None
        self.orig_class = None


    def fit(self, X, y):
        self.class_data = np.mat(y).transpose() * np.mat(X)
        self.orig_data = X
        self.orig_class = y

    def predict(self, X):
        impostors_amount = 5
        top_similar = 3
        for x in X:
            for i, y in enumerate(self.class_data):
                impostors = self.orig_data[np.array(self.orig_class[:,i] == 0).flatten()]
                # pick random top 5 impostors
                np.random.shuffle(impostors)
                impostors = impostors[:impostors_amount]

                distances = self.cals_distances(impostors, x, y)
                sorted_distances = distances.argsort()

                # top 3 similar
                same_author = (same_author[:top_similar] == impostors_amount).any()


    def cals_distances(impostors, x, y):
        # impostors[:, np.newaxis] - y # only if all y are sent (y is two dimensional matrix)
        y_distance = np.power(impostors - y, 2).sum(axis = -1)
        x_distance = np.power(impostors - x, 2).sum(axis = -1)
        imposters_two_way_distance = np.sqrt(y_distance) * np.sqrt(x_distance)

        two_way_distance = np.power(x - y, 2).sum(axis = -1)


	return np.append(imposters_two_way_distance,two_way_distance)
	

from sklearn.pipeline import make_pipeline

from sklearn import preprocessing

from sklearn.feature_extraction.text import TfidfTransformer

from sklearn.ensemble import ExtraTreesClassifier
#from sklearn.feature_selection import SelectFromModel

from sklearn import svm
from sklearn import naive_bayes
from sklearn import neighbors
from sklearn import linear_model
from sklearn import neural_network
#single_classifier = svm.SVC(kernel='polynomial', C=4)

#single_classifier = svm.SVC(kernel='linear', cache_size = 2048)

#single_classifier = neural_network.MLPClassifier(hidden_layer_sizes=10 * (100,))

single_classifier = svm.LinearSVC()

#single_classifier = naive_bayes.GaussianNB()
#single_classifier = naive_bayes.MultinomialNB()
#single_classifier = naive_bayes.BernoulliNB()

#single_svc = svm.SVC(kernel='rbf', cache_size = 2048)

single_classifier = make_pipeline(TfidfTransformer(), single_classifier)
#single_classifier = make_pipeline(preprocessing.StandardScaler(), single_classifier)
#single_classifier = make_pipeline(SelectFromModel(ExtraTreesClassifier(), prefit = False), TfidfTransformer(), single_classifier)

#classifier = OneVsRestClassifier(make_pipeline(preprocessing.StandardScaler(),single_classifier))

classifier = OneVsRestClassifier(single_classifier)

# learn_data = preprocessing.scale(learn_data)

#classifier = make_pipeline(preprocessing.StandardScaler(), classifier)

#classifier = make_pipeline(SelectFromModel(ExtraTreesClassifier(), prefit = False), OneVsRestClassifier(single_classifier))

#classifier = make_pipeline(SelectFromModel(ExtraTreesClassifier(), prefit = False), single_classifier)

#classifier = single_classifier

#classifier = OneVsOneClassifierMultiLabel(single_classifier)

#classifier = neighbors.KNeighborsClassifier()

#classifier = make_pipeline(TfidfTransformer(), neighbors.KNeighborsClassifier())
#classifier = linear_model.Ridge()


print "running", classifier
TEST = True

if not TEST:

    trained_classifier = classifier.fit(learn_data, labels)

    from sklearn.externals import joblib
    import cPickle as pickle
    import os
    try:
        os.makedirs('classifier_data')
    except OSError, e:
        pass
    joblib.dump(trained_classifier, 'classifier_data/linear_svc_classifier.jlb') 
    pickle.dump(lb, open("classifier_data/label_binarizer.pkl", "wb"))
else:


    from sklearn import metrics
    from functools import partial
    f1_scorer_no_average = metrics.make_scorer(partial(metrics.f1_score, average=None))

    def multilabel_score(estimator, X_test, y_test, scorer):
        """Compute the score of an estimator on a given test set."""
        if y_test is None:
            score = scorer(estimator, X_test)
        else:
            score = scorer(estimator, X_test, y_test)
        if getattr(scorer, 'keywords', {}).get('average', None) is None:
            return list(score)
        elif not isinstance(score, numbers.Number):
            raise ValueError("scoring must return a number, got %s (%s) instead."
                             % (str(score), type(score)))
        return list(score)
    from sklearn import cross_validation
    cross_validation._score = multilabel_score

    import warnings
    from sklearn.metrics.base import UndefinedMetricWarning
    def default_nan_prf_divide(numerator, denominator, metric, modifier, average, warn_for):
        """Performs division and handles divide-by-zero.

        On zero-division, sets the corresponding result elements to zero
        and raises a warning.

        The metric, modifier and average arguments are used only for determining
        an appropriate warning.
        """
        result = numerator.astype(np.float_) / denominator.astype(np.float_)
        mask = denominator == 0.0
        if not np.any(mask):
            return result

        # remove infs
        if average is None:
            result[mask] = np.nan
        else:
            result[mask] = 0.0

        # build appropriate warning
        # E.g. "Precision and F-score are ill-defined and being set to 0.0 in
        # labels with no predicted samples"
        axis0 = 'sample'
        axis1 = 'label'
        if average == 'samples':
            axis0, axis1 = axis1, axis0

        if metric in warn_for and 'f-score' in warn_for:
            msg_start = '{0} and F-score are'.format(metric.title())
        elif metric in warn_for:
            msg_start = '{0} is'.format(metric.title())
        elif 'f-score' in warn_for:
            msg_start = 'F-score is'
        else:
            return result

        msg = ('{0} ill-defined and being set to np.nan {{0}} '
               'no {1} {2}s.'.format(msg_start, modifier, axis0))
        if len(mask) == 1:
            msg = msg.format('due to')
        else:
            msg = msg.format('in {0}s with'.format(axis1))
        warnings.warn(msg, UndefinedMetricWarning, stacklevel=2)
        return result

    from sklearn.metrics import classification
    _precision_recall_fscore_support = classification.precision_recall_fscore_support
    def precision_recall_fscore_support(*args, **kargs):
        precision, recall, f_score, true_sum = _precision_recall_fscore_support(*args, **kargs)
        if kargs.get('average', None) is None:
            f_score[np.isnan(precision) * np.isnan(recall)] = 1.0 # both true_sum and pred_sum are 0
        return precision, recall, f_score, true_sum
    classification.precision_recall_fscore_support = precision_recall_fscore_support
    classification._prf_divide = default_nan_prf_divide

    from sklearn import cross_validation
    from sklearn.utils.multiclass import type_of_target
    from copy import deepcopy
    _cross_val_score = cross_validation.cross_val_score
    def cross_val_score_one_vs_all_per_class(estimator, X, y=None, *args, **kargs):
        y_type = type_of_target(y)
        positive_example_amount = y.sum(axis=0)
        error = ""
        if (positive_example_amount < kargs['cv']).any():
            error = str((positive_example_amount < kargs['cv']).sum()) + " : too little examples for " + str(np.where(positive_example_amount < kargs['cv'])) + str(positive_example_amount[np.where(positive_example_amount < kargs['cv'])])
        if (positive_example_amount > y.shape[0] - kargs['cv']).any():
            error += str((positive_example_amount > y.shape[0] - kargs['cv']).sum()) + " : too many examples for " + str(np.where(positive_example_amount > y.shape[0] - kargs['cv'])) + str(positive_example_amount[np.where(positive_example_amount > y.shape[0] - kargs['cv'])])
#        if error:
#            raise Exception(error)
        if y_type.startswith('multilabel') and isinstance(estimator, OneVsRestClassifier):
            res = []
            for yy in y.transpose():
                res.append(_cross_val_score(deepcopy(estimator.estimator), X, yy, *args, **kargs))
            import pdb; pdb.set_trace()
        else:
            res = _cross_val_score(estimator, X, y, *args, **kargs)
        return np.array(list(res))
#    cross_validation.cross_val_score = cross_val_score_one_vs_all_per_class

    scores = cross_validation.cross_val_score(classifier, learn_data, labels, scoring=f1_scorer_no_average, cv=10)# 'f1_weighted')
    scores = np.array(list(scores))
    import IPython; IPython.embed()
    print "Accuracy: %0.2f (+/- %0.2f)" % (scores.mean(), scores.std() * 2)




#print >>sys.stderr, 'learning data'; sys.stderr.flush()
#trained_classifier = classifier.fit(learn_data[:-10], labels[:-10])
#print >>sys.stderr, 'classifying'; sys.stderr.flush()
#predicted_labels = trained_classifier.predict(learn_data[-10:])
#predicted_tags = lb.inverse_transform(predicted_labels)
#
#from pprint import pprint
#for _predicted_tags, _tags, _d in zip(predicted_tags, tags[-10:], data[-10:]):
#	print _d['id'],'--',
#	for _predicted_tag in _predicted_tags:
#		print _predicted_tag[::-1], ",",
#	print "-",
#	for _tag in _tags:
#		print _tag[::-1], ",",
#	print ""



import IPython; IPython.embed()
