from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
import operator
import numpy as np
import matplotlib.pyplot as plt
from itertools import chain
import matplotlib.patches as mpatches
import string

def main():
    conf = SparkConf().setMaster("local[2]").setAppName("Streamer")
    sc = SparkContext(conf=conf)
    ssc = StreamingContext(sc, 10)   # Create a streaming context with batch interval of 10 sec
    ssc.checkpoint("checkpoint")

    pwords = load_wordlist("positive.txt")
    nwords = load_wordlist("negative.txt")
   
    counts = stream(ssc, pwords, nwords, 10)
    make_plot(counts)


def make_plot(counts):
    """
    Plot the counts for the positive and negative words for each timestep.
    Use plt.show() so that the plot will popup.
    """
    positive_values = []
    negative_values = []
    for split_count in counts:
    	for each_tuple in split_count:
    		if each_tuple[0] == 'positive':
    			positive_values.append(each_tuple[1])
    		else:
    			negative_values.append(each_tuple[1])

    range_x = []
    for i in range(len(positive_values)):
    	range_x.append(i)

    
    positive_plot, = plt.plot(range_x,positive_values, marker='o')
    #blue_patch = mpatches.Patch(color='blue', label='positive')
    #plt.legend(handles=[blue_patch])
    negative_plot, = plt.plot(range_x,negative_values, marker='o')
    #green_patch = mpatches.Patch(color='green', label='negative')
    #plt.legend(handles=[green_patch])
    plt.xticks(range_x) #remove float values on x axis
    plt.legend([positive_plot, negative_plot], ["positive", "negative"], loc = 2)
    plt.xlabel('Time step')
    plt.ylabel('Word count')
    plt.margins(0.1, 0.05) #add padding
    plt.show()



def load_wordlist(filename):
    """ 
    This function should return a list or set of words from the given filename.
    """
    text_file = open(filename, "r")
    lines = text_file.readlines()
    for i in range(len(lines)):
    	lines[i] = lines[i].rstrip('\n').split(',')
    lines = list(chain.from_iterable(lines))
    return lines

def decide_class(x, pwords, nwords):
	x = x.translate(string.maketrans("",""), string.punctuation).lower() #remove any punctuation, convert to lowercase
	#reference: http://stackoverflow.com/questions/16050952/how-to-remove-all-the-punctuation-in-a-string-python
	if x in pwords or x in nwords:
		return True
	else:
		return False

def pos_neg(x, pwords):
	if x in pwords:
		return "positive"
	else:
		return "negative"


def updateFunction(newValues, runningCount):
    if runningCount is None:
       runningCount = 0
    return sum(newValues, runningCount)

def stream(ssc, pwords, nwords, duration):
    kstream = KafkaUtils.createDirectStream(
        ssc, topics = ['twitterstream'], kafkaParams = {"metadata.broker.list": 'localhost:9092'})
    tweets = kstream.map(lambda x: x[1].encode("ascii","ignore"))
    #print "HEllo"
    #tweets.pprint()
    words = tweets.flatMap(lambda line: line.split(" "))
    words = words.filter(lambda x: decide_class(x, pwords, nwords)).map(lambda x: (pos_neg(x, pwords), 1)).reduceByKey(lambda x, y: x+ y)
    words1 = words.updateStateByKey(updateFunction)
    words1.pprint() #print the positive, negative tweets with running total
    
    counts = []
    words.foreachRDD(lambda t, rdd: counts.append(rdd.collect()))
    #print counts
    
    ssc.start()                         # Start the computation
    ssc.awaitTerminationOrTimeout(duration)
    ssc.stop(stopGraceFully=True)

    return counts


if __name__=="__main__":
    main()
