# -*- coding: utf-8 -*-
"""
Created on Wed Jul 18 19:50:15 2018

@author: kalvi
"""

## Load Dependencies
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

#import json, os, re, shutil, sys, time
import os, shutil, time
#from importlib import reload
from imp import reload
#import collections, itertools
import unittest
#from trainer import unittest
#from . import unittest
#import trainer.unittest as unittest
#from IPython.display import display, HTML

# NLTK for NLP utils and corpora
#import nltk

# NumPy and TensorFlow
import numpy as np
import tensorflow as tf
assert(tf.__version__.startswith("1."))

# Helper libraries
#from trainer import utils#, vocabulary, tf_embed_viz
#import utils
import trainer.utils as utils

# rnnlm code
#from trainer import rnnlm
import trainer.rnnlm as rnnlm
reload(rnnlm)
#from trainer import rnnlm_test
#import trainer.rnnlm_test as rnnlm_test
#reload(rnnlm_test)
#from . import rnnlm; reload(rnnlm)
#from . import rnnlm_test; reload(rnnlm_test)
#import rnnlm; reload(rnnlm)
#import rnnlm_test; reload(rnnlm_test)
# packages for extracting data
import pandas as pd

#
#import cloudstorage as gcs
import random
import csv

def make_tensorboard(tf_graphdir="/tmp/artificial_hotel_reviews/a4_graph", V=100, H=1024, num_layers=2):
    reload(rnnlm)
    TF_GRAPHDIR = tf_graphdir
    # Clear old log directory.
    shutil.rmtree(TF_GRAPHDIR, ignore_errors=True)
    
    lm = rnnlm.RNNLM(V=V, H=H, num_layers=num_layers)
    lm.BuildCoreGraph()
    lm.BuildTrainGraph()
    lm.BuildSamplerGraph()
    summary_writer = tf.summary.FileWriter(TF_GRAPHDIR, lm.graph)
    return summary_writer

# Unit Tests
def test_graph():
    reload(rnnlm); reload(rnnlm_test)
    utils.run_tests(rnnlm_test, ["TestRNNLMCore", "TestRNNLMTrain", "TestRNNLMSampler"])

def test_training():
    reload(rnnlm); reload(rnnlm_test)
    th = rnnlm_test.RunEpochTester("test_toy_model")
    th.setUp(); th.injectCode(run_epoch, score_dataset)
    unittest.TextTestRunner(verbosity=2).run(th)

def score_each_step(lm, session, ids):
    #no batching
    bi = utils.rnnlm_batch_generator(ids, batch_size=100, max_time=100)
    for i, (w,y) in enumerate(bi):
        if i == 0:
            h = session.run(lm.initial_h_, {lm.input_w_: w})
        feed_dict = {lm.input_w_:w,
                     lm.target_y_:y,
                     lm.learning_rate_: 0.002,
                     lm.use_dropout_: False,
                     lm.initial_h_:h}
        cost, h, _ = session.run([loss, lm.final_h_, train_op],feed_dict=feed_dict)
        #pick up here
        
## Training Functions
def run_epoch(lm, session, batch_iterator,
              train=False, verbose=False,
              tick_s=10, learning_rate=None):
    assert(learning_rate is not None)
    start_time = time.time()
    tick_time = start_time  # for showing status
    total_cost = 0.0  # total cost, summed over all words
    total_batches = 0
    total_words = 0

    if train:
        train_op = lm.train_step_
        use_dropout = True
        loss = lm.train_loss_
    else:
        train_op = tf.no_op()
        use_dropout = False  # no dropout at test time
        loss = lm.loss_  # true loss, if train_loss is an approximation

    for i, (w, y) in enumerate(batch_iterator):
        cost = 0.0
        # At first batch in epoch, get a clean intitial state.
        if i == 0:
            h = session.run(lm.initial_h_, {lm.input_w_: w})

        #### YOUR CODE HERE ####
        feed_dict = {lm.input_w_:w,
                     lm.target_y_:y,
                     lm.learning_rate_: learning_rate,
                     lm.use_dropout_: use_dropout,
                     lm.initial_h_:h}
        cost, h, _ = session.run([loss, lm.final_h_, train_op],feed_dict=feed_dict)

        #### END(YOUR CODE) ####
        total_cost += cost
        total_batches = i + 1
        total_words += w.size  # w.size = batch_size * max_time

        ##
        # Print average loss-so-far for epoch
        # If using train_loss_, this may be an underestimate.
        if verbose and (time.time() - tick_time >= tick_s):
            avg_cost = total_cost / total_batches
            avg_wps = total_words / (time.time() - start_time)
            print("[batch {:d}]: seen {:d} words at {:.1f} wps, loss = {:.3f}".format(
                i, total_words, avg_wps, avg_cost))
            tick_time = time.time()  # reset time ticker

    return total_cost / total_batches

def score_dataset(lm, session, ids, name="Data"):
    # For scoring, we can use larger batches to speed things up.
    bi = utils.rnnlm_batch_generator(ids, batch_size=100, max_time=100)
    cost = run_epoch(lm, session, bi, 
                     learning_rate=0.0, train=False, 
                     verbose=False, tick_s=3600)
    print("{:s}: avg. loss: {:.03f}  (perplexity: {:.02f})".format(name, cost, np.exp(cost)))
    return cost


#build a list of list of characters from the 5-star reviews
def preprocess_review_series(review_series):
    review_list = []
    for new_review in review_series:
        clipped_review = new_review[2:-1]
        char_list = list(clipped_review.lower())
        semifinal_review = []
        last_char = ''
        for ascii_char in char_list:
            if ascii_char == '\\' or last_char == '\\':
                pass
            else:
                semifinal_review.append(ascii_char)
            last_char = ascii_char
        if len(semifinal_review) > 300:
            final_review = ['<SOR>'] + semifinal_review + ['<EOR>']
            #print(final_review)
            review_list.append(final_review)
    return review_list

def get_review_series(review_path = '/home/kalvin_kao/yelp_challenge_dataset/review.csv'):
    #review_path = '/home/kalvin_kao/yelp_challenge_dataset/review.csv'
    review_df = pd.read_csv(review_path)
    five_star_review_df = review_df[review_df['stars']==5]
    #five_star_review_series = five_star_review_df['text']
    return five_star_review_df['text']

def get_business_list(business_path = '/home/kalvin_kao/yelp_challenge_dataset/business.csv'):
    #business_path = '/home/kalvin_kao/yelp_challenge_dataset/business.csv'
    return pd.read_csv(business_path)

def split_train_test(review_list, training_samples, test_samples):
    #pass in randomized review list
    train_len = int(np.floor(0.8*len(review_list)))
    test_len = int(np.floor(0.2*len(review_list)))
    training_review_list = review_list[:train_len]
    testing_review_list = review_list[-test_len:]
    randomized_training_list = random.sample(training_review_list, training_samples)
    randomized_testing_list = random.sample(testing_review_list, test_samples)
    training_review_list = [item for sublist in randomized_training_list for item in sublist]
    print("number of training characters", len(training_review_list))
    test_review_list = [item for sublist in randomized_testing_list for item in sublist]
    print("number of test characters", len(test_review_list))
    return randomized_training_list, randomized_testing_list

def make_train_test_data(five_star_review_series, training_samples=20000, test_samples=1000):
    #fix randomization to prevent evaluation on trained samples
    review_list = preprocess_review_series(five_star_review_series)
    #split and shuffle the data
    train_len = int(np.floor(0.8*len(review_list)))
    test_len = int(np.floor(0.2*len(review_list)))
    np.random.shuffle(review_list)
    training_review_list = review_list[:train_len]
    testing_review_list = review_list[-test_len:]
    randomized_training_list = random.sample(training_review_list, training_samples)
    randomized_testing_list = random.sample(testing_review_list, test_samples)
    #training_review_list = [item for sublist in review_list[:training_samples] for item in sublist]
    training_review_list = [item for sublist in randomized_training_list for item in sublist]
    print("number of training characters", len(training_review_list))
    
    #test_review_list = [item for sublist in review_list[training_samples:training_samples+test_samples] for item in sublist]
    test_review_list = [item for sublist in randomized_testing_list for item in sublist]
    print("number of test characters", len(test_review_list))
    return training_review_list, test_review_list


#def make_vocabulary(training_review_list, test_review_list):
#    unique_characters = list(set(training_review_list + test_review_list))
#    #vocabulary
#    char_dict = {w:i for i, w in enumerate(unique_characters)}
#    ids_to_words = {v: k for k, v in char_dict.items()}
#    return char_dict, ids_to_words
def make_vocabulary(dataset_list):
    unique_characters = list(set().union(*dataset_list))
    #unique_characters = list(set(training_review_list + test_review_list))
    #vocabulary
    char_dict = {w:i for i, w in enumerate(unique_characters)}
    ids_to_words = {v: k for k, v in char_dict.items()}
    return char_dict, ids_to_words

def convert_to_ids(char_dict, review_list):
    #convert to flat (1D) np.array(int) of ids
    review_ids = [char_dict.get(token) for token in review_list]
    return np.array(review_ids)

def run_training(train_ids, test_ids, tf_savedir, model_params, max_time=100, batch_size=256, learning_rate=0.002, num_epochs=20):
    #V = len(words_to_ids.keys())
    # Training parameters
    ## add parameter sets for each attack/defense configuration
    #max_time = 25
    #batch_size = 100
    #learning_rate = 0.01
    #num_epochs = 10
    
    # Model parameters
    #model_params = dict(V=vocab.size, 
                        #H=200, 
                        #softmax_ns=200,
                        #num_layers=2)
    #model_params = dict(V=len(words_to_ids.keys()), 
                        #H=1024, 
                        #softmax_ns=len(words_to_ids.keys()),
                        #num_layers=2)
    #model_params = dict(V=V, H=H, softmax_ns=softmax_ns, num_layers=num_layers)
    
    #TF_SAVEDIR = "/tmp/artificial_hotel_reviews/a4_model"
    TF_SAVEDIR = tf_savedir
    checkpoint_filename = os.path.join(TF_SAVEDIR, "rnnlm")
    trained_filename = os.path.join(TF_SAVEDIR, "rnnlm_trained")
    
    # Will print status every this many seconds
    #print_interval = 5
    print_interval = 30
    
    lm = rnnlm.RNNLM(**model_params)
    lm.BuildCoreGraph()
    lm.BuildSamplerGraph()
    lm.BuildTrainGraph()
    
    # Explicitly add global initializer and variable saver to LM graph
    with lm.graph.as_default():
        initializer = tf.global_variables_initializer()
        saver = tf.train.Saver()
        
    # Clear old log directory
    shutil.rmtree(TF_SAVEDIR, ignore_errors=True)
    if not os.path.isdir(TF_SAVEDIR):
        os.makedirs(TF_SAVEDIR)
    
    with tf.Session(graph=lm.graph) as session:
        # Seed RNG for repeatability
        #tf.set_random_seed(42)
    
        session.run(initializer)
        
        #check trainable variables
        #variables_names = [v.name for v in tf.trainable_variables()]
        #values = session.run(variables_names)
        #for k, v in zip(variables_names, values):
            #print("Variable: ", k)
            #print("Shape: ", v.shape)
            #print(v)
    
        for epoch in range(1,num_epochs+1):
            t0_epoch = time.time()
            bi = utils.rnnlm_batch_generator(train_ids, batch_size, max_time)
            print("[epoch {:d}] Starting epoch {:d}".format(epoch, epoch))
            # Run a training epoch.
            run_epoch(lm, session, batch_iterator=bi, train=True, verbose=True, tick_s=10, learning_rate=learning_rate)
    
            print("[epoch {:d}] Completed in {:s}".format(epoch, utils.pretty_timedelta(since=t0_epoch)))
        
            # Save a checkpoint
            saver.save(session, checkpoint_filename, global_step=epoch)
        
            ##
            # score_dataset will run a forward pass over the entire dataset
            # and report perplexity scores. This can be slow (around 1/2 to 
            # 1/4 as long as a full epoch), so you may want to comment it out
            # to speed up training on a slow machine. Be sure to run it at the 
            # end to evaluate your score.
            print("[epoch {:d}]".format(epoch), end=" ")
            score_dataset(lm, session, train_ids, name="Train set")
            print("[epoch {:d}]".format(epoch), end=" ")
            score_dataset(lm, session, test_ids, name="Test set")
            print("")
        
        # Save final model
        saver.save(session, trained_filename)
        return trained_filename

def get_char_probs(trained_filename, model_params, test_ids):
    lm = rnnlm.RNNLM(**model_params)
    lm.BuildCoreGraph()
    all_review_likelihoods = []
    train_op = tf.no_op()
    use_dropout = False
    loss = lm.loss_
    
    with lm.graph.as_default():
        saver = tf.train.Saver()
    
    with tf.Session(graph=lm.graph) as session:
        #train_op = tf.no_op()
        #use_dropout = False
        #loss = lm.loss_
        
        saver.restore(session, trained_filename)
        
        for review in test_ids:
            review_likelihoods = []
            inputs = review[:-1]
            labels = review[1:]
            inputs_labels = zip(inputs,labels)
            for i, (w,y) in enumerate(inputs_labels):
                
                w = np.array(w)
                y = np.array(y)
                w = w.reshape([1,1])
                y = y.reshape([1,1])
                
                if i == 0:
                    h = session.run(lm.initial_h_, {lm.input_w_: w})

                feed_dict = {lm.input_w_:w, 
                             lm.target_y_:y,
                             lm.learning_rate_: 0.002,
                             lm.use_dropout_: use_dropout,
                             lm.initial_h_:h}
                cost, h = session.run([loss, lm.final_h_],feed_dict=feed_dict)
                likelihood = 2**(-1*cost)
                review_likelihoods.append(likelihood)
            all_review_likelihoods.append(review_likelihoods)
    return all_review_likelihoods

## Sampling
def sample_step(lm, session, input_w, initial_h):
    """Run a single RNN step and return sampled predictions.
  
    Args:
      lm : rnnlm.RNNLM
      session: tf.Session
      input_w : [batch_size] vector of indices
      initial_h : [batch_size, hidden_dims] initial state
    
    Returns:
      final_h : final hidden state, compatible with initial_h
      samples : [batch_size, 1] vector of indices
    """
    # Reshape input to column vector
    input_w = np.array(input_w, dtype=np.int32).reshape([-1,1])

    # Run sample ops
    feed_dict = {lm.input_w_:input_w, lm.initial_h_:initial_h}
    final_h, samples = session.run([lm.final_h_, lm.pred_samples_], feed_dict=feed_dict)

    # Note indexing here: 
    #   [batch_size, max_time, 1] -> [batch_size, 1]
    return final_h, samples[:,-1,:]

def generate_text(trained_filename, model_params, words_to_ids, ids_to_words):
    # Same as above, but as a batch
    #max_steps = 20
    max_steps = 300
    num_samples = 50
    random_seed = 42
    
    lm = rnnlm.RNNLM(**model_params)
    lm.BuildCoreGraph()
    lm.BuildSamplerGraph()
    
    with lm.graph.as_default():
        saver = tf.train.Saver()
    
    with tf.Session(graph=lm.graph) as session:
        # Seed RNG for repeatability
        #tf.set_random_seed(random_seed)
        
        # Load the trained model
        saver.restore(session, trained_filename)
    
        # Make initial state for a batch with batch_size = num_samples
        #w = np.repeat([[vocab.START_ID]], num_samples, axis=0)
        w = np.repeat([[words_to_ids.get('<SOR>')]], num_samples, axis=0)
        h = session.run(lm.initial_h_, {lm.input_w_: w})
        # take one step for each sequence on each iteration 
        for i in range(max_steps):
            h, y = sample_step(lm, session, w[:,-1:], h)
            w = np.hstack((w,y))
    
        # Print generated sentences
        for row in w:
            print(trained_filename, end=":  ")
            for i, word_id in enumerate(row):
                #print(vocab.id_to_word[word_id], end=" ")
                print(ids_to_words[word_id], end="")
                #if (i != 0) and (word_id == vocab.START_ID):
                if (i != 0) and (word_id == words_to_ids.get("<EOR>")):
                    break
            print("")

def train_attack_model(training_samples=20000, test_samples=1000, review_path = '/home/kalvin_kao/yelp_challenge_dataset/review.csv'):
    #training_samples=20000
    #test_samples=1000
    #review_path = '/home/kalvin_kao/yelp_challenge_dataset/review.csv'
    start_format = time.time()
    five_star_reviews = get_review_series(review_path)
    train_review_list, test_review_list = make_train_test_data(five_star_reviews, training_samples, test_samples)
    words_to_ids, ids_to_words = make_vocabulary(train_review_list, test_review_list)
    train_ids = convert_to_ids(words_to_ids, train_review_list)
    test_ids = convert_to_ids(words_to_ids, test_review_list)
    end_format = time.time()
    print("data formatting took " + str(end_format-start_format) + " seconds")
    model_params = dict(V=len(words_to_ids.keys()), 
                            H=1024, 
                            softmax_ns=len(words_to_ids.keys()),
                            num_layers=2)
    #run_training(train_ids, test_ids, tf_savedir, model_params, max_time=100, batch_size=256, learning_rate=0.002, num_epochs=20)
    trained_filename = run_training(train_ids, test_ids, tf_savedir = "/tmp/artificial_hotel_reviews/a4_model", model_params=model_params, max_time=150, batch_size=256, learning_rate=0.002, num_epochs=20)
    return trained_filename, model_params, words_to_ids, ids_to_words

def neg_log_lik_ratio(likelihoods_real, likelihoods_artificial):
    predictions = []
    combined = zip(likelihoods_real, likelihoods_artificial)
    for (real_review_likelihoods, artificial_review_likelihoods) in combined:
        negative_log_lik_ratios = -1*(np.log(np.divide(real_review_likelihoods, artificial_review_likelihoods)))
        #averaged_llrs = negative_log_lik_ratios[:-1]/(len(negative_log_lik_ratios)-1)
        averaged_llrs = np.sum(negative_log_lik_ratios[:-1])/(len(negative_log_lik_ratios)-1)
        predictions.append(averaged_llrs)
    return predictions

#get data from gcs
#review_path = 'gs://w266_final_project_kk/data/review.csv'
#train_review_path = 'gs://w266_final_project_kk/data/split01_train_data_01.csv'
#test_review_path = 'gs://w266_final_project_kk/data/split01_test_data_01.csv'
start_dl = time.time()
os.system('gsutil -q cp gs://w266_final_project_kk/data/split01_train_data_02.csv .')
os.system('gsutil -q cp gs://w266_final_project_kk/data/split01_test_data_02.csv .')
os.system('gsutil -q cp gs://w266_final_project_kk/data/gen01_train_data_01.csv .')
os.system('gsutil -q cp gs://w266_final_project_kk/data/gen01_test_data_01.csv .')
end_dl = time.time()
print("data download took " + str(end_dl-start_dl) + " seconds")
#gsutil cp gs://[BUCKET_NAME]/[OBJECT_NAME] [OBJECT_DESTINATION]
real_train_review_path = './split01_train_data_02.csv'
real_test_review_path = './split01_test_data_02.csv'
artificial_train_review_path = './gen01_train_data_01.csv'
artificial_test_review_path = './gen01_test_data_01.csv'

#trained_filename, model_params, words_to_ids, ids_to_words = train_attack_model(training_samples=25000, 
                                                                                #test_samples=6250, 
                                                                                #review_path = review_path)


start_open = time.time()
with open(real_train_review_path, 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    training_review_list_real = [item for sublist in reader for item in sublist]

with open(real_test_review_path, 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    test_review_list_real = [sublist for sublist in reader]
    #make into list of list
test_review_list_real_training_eval = [item for sublist in test_review_list_real for item in sublist]

with open(artificial_train_review_path, 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    training_review_list_artificial = [item for sublist in reader for item in sublist]

with open(artificial_test_review_path, 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    test_review_list_artificial = [sublist for sublist in reader]
    #make into list of list
test_review_list_artificial_training_eval = [item for sublist in test_review_list_artificial for item in sublist]
end_open = time.time()
print("data reading took " + str(end_open-start_open) + " seconds")

start_vocab = time.time()
words_to_ids, ids_to_words = make_vocabulary([training_review_list_real, test_review_list_real_training_eval, training_review_list_artificial, test_review_list_artificial_training_eval])
train_ids_real = convert_to_ids(words_to_ids, training_review_list_real)
test_ids_real = [convert_to_ids(words_to_ids, review) for review in test_review_list_real]
test_ids_real_training_eval = convert_to_ids(words_to_ids, test_review_list_real_training_eval)
train_ids_artificial = convert_to_ids(words_to_ids, training_review_list_artificial)
test_ids_artificial = [convert_to_ids(words_to_ids, review) for review in test_review_list_artificial]
test_ids_artificial_training_eval = convert_to_ids(words_to_ids, test_review_list_artificial_training_eval)
end_vocab = time.time()
print("vocabulary building took " + str(end_vocab-start_vocab) + " seconds")

start_training = time.time()
model_params = dict(V=len(words_to_ids.keys()), H=1024, softmax_ns=len(words_to_ids.keys()), num_layers=2)
#trained_filename_real = run_training(train_ids_real, test_ids_real_training_eval, tf_savedir = "/tmp/defense_model/real", model_params=model_params, max_time=150, batch_size=128, learning_rate=0.002, num_epochs=20)
#trained_filename_artificial = run_training(train_ids_artificial, test_ids_artificial_training_eval, tf_savedir = "/tmp/defense_model/artificial", model_params=model_params, max_time=150, batch_size=128, learning_rate=0.002, num_epochs=20)
trained_filename_real = run_training(train_ids_real[:len(train_ids_artificial)], test_ids_real_training_eval[:1000000], tf_savedir = "/tmp/defense_model/real", model_params=model_params, max_time=150, batch_size=128, learning_rate=0.002, num_epochs=20)#UPDATE FOR ACTUAL RUN
trained_filename_artificial = run_training(train_ids_artificial, test_ids_artificial_training_eval[:1000000], tf_savedir = "/tmp/defense_model/artificial", model_params=model_params, max_time=150, batch_size=128, learning_rate=0.002, num_epochs=20)#UPDATE FOR ACTUAL RUN
end_training = time.time()
print("overall training took " + str(end_training-start_training) + " seconds")

### UPDATED!!!
#save both RNNs for later use
save_command_1  = "gsutil cp -r " + trained_filename_real[0:trained_filename_real.rfind("/")] + " gs://w266_final_project_kk/defense_baseline/real/" + str(int(np.floor(time.time())))
save_command_2  = "gsutil cp -r " + trained_filename_artificial[0:trained_filename_artificial.rfind("/")] + " gs://w266_final_project_kk/defense_baseline/artificial/" + str(int(np.floor(time.time())))
#save_command_1  = "gsutil cp -r " + trained_filename_real[0:trained_filename_real.rfind("/")] + " gs://w266_final_project_kk/practice_run/defense_real/" + str(int(np.floor(time.time())))
#save_command_2  = "gsutil cp -r " + trained_filename_artificial[0:trained_filename_artificial.rfind("/")] + " gs://w266_final_project_kk/practice_run/defense_artificial/" + str(int(np.floor(time.time())))
os.system(save_command_1)
os.system(save_command_2)
### UPDATED!!!

#generate examples from each RNN out of curiosity
start_sampling = time.time()
generate_text(trained_filename_real, model_params, words_to_ids, ids_to_words)
generate_text(trained_filename_artificial, model_params, words_to_ids, ids_to_words)
end_sampling = time.time()
print("character sampling took " + str(end_sampling-start_sampling) + " seconds")

#first feed the real reviews into each RNN and get the softmax probability of each character
#get the classification for real reviews by forming an average negative log-likelihood ratio for each review
start_scoring = time.time()
test_likelihoods_real_from_real = get_char_probs(trained_filename_real, model_params, test_ids_real[:1000])
test_likelihoods_real_from_artificial = get_char_probs(trained_filename_artificial, model_params, test_ids_real[:1000])
predictions_real = neg_log_lik_ratio(test_likelihoods_real_from_real, test_likelihoods_real_from_artificial)
#negative_log_lik_ratios = -1*(np.log(np.divide(test_likelihoods_real_from_real, test_likelihoods_real_from_artificial)))
#predictor = 

#next feed the generated reviews into each RNN and get the softmax probability of each character
#get the classification for generated reviews by forming an average negative log-likelihood ratio for each review
test_likelihoods_artificial_from_real = get_char_probs(trained_filename_real, model_params, test_ids_artificial[:1000])
test_likelihoods_artificial_from_artificial = get_char_probs(trained_filename_artificial, model_params, test_ids_artificial[:1000])
predictions_artificial = neg_log_lik_ratio(test_likelihoods_artificial_from_real, test_likelihoods_artificial_from_artificial)
end_scoring = time.time()
print("review scoring took " + str(end_scoring-start_scoring) + " seconds")

### UPDATED!!!
predictions_real = np.array(predictions_real)
predictions_artificial = np.array(predictions_artificial)
np.savetxt("predictions_real.csv", predictions_real, delimiter=",")
np.savetxt("predictions_artificial.csv", predictions_artificial, delimiter=",")
os.system("gsutil cp predictions_real.csv gs://w266_final_project_kk/defense_baseline/predictions_real/")
os.system("gsutil cp predictions_artificial.csv gs://w266_final_project_kk/defense_baseline/predictions_artificial/")
#os.system("gsutil cp predictions_real.csv gs://w266_final_project_kk/practice_run/defense_predictions_real/")
#os.system("gsutil cp predictions_artificial.csv gs://w266_final_project_kk/practice_run/defense_predictions_artificial/")
### UPDATED!!!
    
#test_graph()
#test_training()
#save_command = "gsutil -q cp " + trained_filename + " gs://w266_final_project_kk/" + time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime())
#save_command = "gsutil -q cp " + trained_filename + " gs://w266_final_project_kk/" + str(int(np.floor(time.time())))
#os.system(save_command)