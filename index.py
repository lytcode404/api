from itertools import product
from math import isnan, log10
from unittest import result
from bs4 import BeautifulSoup
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

from flask import Flask, request, jsonify
from flask_cors import CORS
from textblob import TextBlob

app = Flask(__name__)
CORS(app)

# Corrected XPath expressions


def calculate_sentiment_score(arr):
    score = 0

    for text in arr:
        analysis = TextBlob(text)
        score += analysis.sentiment.polarity

    if score > 0:
        return 1
    elif score < 0:
        return -1
    else:
        return 0


def calculate_score(product_info):
    total_weight = 0
    score = 0

    # Rating (weight = 40)  p
    rating = float(product_info["rating"])

    if not isnan(rating):
        # Check if rating is available and valid
        number_of_ratings = float(product_info["numberOfRatings"])
        normalized_rating = min(rating / 5, 1)
        rating_weight = 40 * (log10(number_of_ratings + 1) / log10(1001))
        score += normalized_rating * rating_weight
        total_weight += rating_weight

    # Number of reviews (weight = 10)  q
    num_reviews = float(product_info["numReviews"])
    score += min(num_reviews / 100, 1) * 10
    total_weight += 10

    # Sentiment of reviews (weight = 20)  r
    review_arr = product_info["reviewArr"]
    sentiment_score = calculate_sentiment_score(review_arr)
    score += 10 * sentiment_score
    total_weight += 10

    # Warranty (weight = 10)  s
    warranty = float(product_info["warranty"])
    if warranty and warranty != 0:
        if warranty == 12:
            score += 10
        elif warranty == 6:
            score += 5
        total_weight += 10

    # Return policy (weight = 5)  t
    return_policy = float(product_info["returnPolicy"])
    score += return_policy
    total_weight += return_policy

    # Delivery charges (weight = 5)  u
    delivery_charges = float(product_info["deliveryCharge"])
    if delivery_charges:
        score += delivery_charges
        total_weight += 5

    # # Delivery time (weight = 5)  v
    # delivery_time = float(product_info["deliveryTime"])
    # if delivery_time:
    #     score += delivery_time
    #     total_weight += 5

    scaled_score = 0 if total_weight == 0 else (score / total_weight) * 100

    return scaled_score


def getVal(url):
    rating = '//*[@id="productRating_LSTACCG48F2YZNGZ8D2LDR2OK_ACCG48F2YZNGZ8D2_"]/div'
    numberOfRatings = '//*[@id="container"]/div/div[3]/div[1]/div[2]/div[2]/div/div[2]/div/div/span[2]/span/span[1]'
    numReviews = '//*[@id="container"]/div/div[3]/div[1]/div[2]/div[2]/div/div[2]/div/div/span[2]/span/span[3]'
    reviewArr = '//*[@id="container"]/div/div[3]/div[1]/div[2]/div[8]/div[6]/div/div[4]'
    warranty = '//*[@id="container"]/div/div[3]/div[1]/div[2]/div[4]/div/div[2]/div'
    returnPolicy = '//*[@id="container"]/div/div[3]/div[1]/div[2]/div[8]/div[1]/div/div[2]/div[2]/ul/li[1]/div'
    deliveryCharge = '//*[@id="container"]/div/div[3]/div[1]/div[2]/div[5]/div/div/div[2]/div[1]/ul/div/div[1]/span[1]'

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Enable headless mode
    driver = webdriver.Chrome(options=options)

    driver.get(url)

    time.sleep(2)

    try:
        rating_val = driver.find_element(
            By.XPATH, rating).get_attribute('innerHTML')
        numberOfRatings_val = driver.find_element(
            By.XPATH, numberOfRatings).get_attribute('innerHTML')
        numReviews_val = driver.find_element(
            By.XPATH, numReviews).get_attribute('innerHTML')

        parent_element = driver.find_element(By.XPATH, reviewArr)
        children = parent_element.find_elements(By.XPATH, '*')

        reviewArr_val = []

        for index, child in enumerate(children[:10], 1):
            inner_html = child.get_attribute('innerHTML')
            soup = BeautifulSoup(inner_html, 'html.parser')
            text = soup.get_text()
            reviewArr_val.append(text)

        warranty_val = driver.find_element(
            By.XPATH, warranty).get_attribute('innerHTML')
        returnPolicy_val = driver.find_element(
            By.XPATH, returnPolicy).get_attribute('innerHTML')
        deliveryCharge_val = driver.find_element(
            By.XPATH, deliveryCharge).get_attribute('innerHTML')

        rating_val2 = re.search(r'(\d+)(?=<img)', rating_val).group(1)

        numberOfRatings_val2 = re.search(
            r'([\d,]+) Ratings', numberOfRatings_val)
        numberOfRatings_val2 = numberOfRatings_val2.group(1).replace(',', '')

        numReviews_val2 = re.search(r'([\d,]+) Reviews', numReviews_val)
        numReviews_val2 = numReviews_val2.group(1).replace(',', '')

        warranty_val2 = re.search(r'\b\d+\b', warranty_val).group()
        returnPolicy_val2 = re.search(r'\b\d+\b', returnPolicy_val).group()
        deliveryCharge_val2 = re.search(r'\b\d+\b', deliveryCharge_val).group()

        product_info = {
            "rating": rating_val2,
            "numberOfRatings": numberOfRatings_val2,
            "numReviews": numReviews_val2,
            "reviewArr": reviewArr_val,
            "warranty": warranty_val2,
            "returnPolicy": returnPolicy_val2,
            "deliveryCharge": deliveryCharge_val2,
        }
        score = calculate_score(product_info)

        product_info["score"] = score

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        product_info = {"error": str(e)}

    finally:
        driver.quit()
        return product_info


@app.route('/catalog_ranking', methods=['POST'])
def get_catalog_ranking():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL not provided"})
    ranking = getVal(url)
    return jsonify(ranking)


if __name__ == '__main__':
    app.run(debug=True)
