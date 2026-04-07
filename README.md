# PickupOpt
---

## Problem Statement

Garbage Collection in the US follows fixed schedule and inefficient routing, leading to:
- High Emissions – heavy duty trucks produce ~25% of transport GHG emissions
- Fuel Inefficiency – garbage trucks get <3mpg and travels ~25000 miles/year leading to excess carbon emission
- High Operational Cost – collection accounts to 40 – 60% of total waste management cost
- Inefficient Pickups

## Project Description
Filter the locations to pick up garbage using predictive analysis. This reduces fuel consumption and thereby carbon emission to a very high extend.  

Use path optimization model to plan pick up routes. 
### Working
Logs the weight of garbage collected per user  
Use this data to predict whether to schedule pick up or not  
  - Done using Google TimesFM that offers zero shot performance across various domains without retraining

Plan the optimized pick-up route based on scheduled pick-ups  

  - Done using Google directionsService API

User can access these information on an integrated dashboard
Deployed using GCP

### System Workflow

1. Garbage data (weight logs) is collected per user. This step is actually done using an embedded system attached to the vehicle. This method helps to avoid user interaction, significantly increasing the reliability and ease of use of the system.
2. TimesFM predicts whether pickup is required  
3. If pickup is needed:  
   - Location is processed using Geocoding API  
   - Optimized routes are generated using Directions API  
4. Results are converted into readable format using Reverse Geocoding API  
5. Data is displayed on a dashboard, the path optimized visit order is given as a priority badge.
6. The webapp is deployed in GCP.
7. The truck refer the priority of each location and visit the locations in that order for optimized path.


### Impact

- Reduces carbon emissions by selecting optimised path and visiting only necessary locations
- Reduces fuel consumption  
- Eliminates inefficient pickups (half-empty or overflow cases)  
- Optimizes operational costs  
- Enables an AI-driven waste management system

---

## Google AI Usage

### Google TimesFM
We used Google TimesFM, a pre-trained time-series foundation model developed by Google Research, to predict garbage generation patterns.

- Logs historical garbage weight per user  
- Performs predictive analysis to determine whether a pickup is required  
- Enables intelligent scheduling instead of fixed routes  
- Reduces unnecessary trips, fuel usage, and emissions  

### Google Maps Platform APIs

#### Directions API
- Used for route optimization  
- Generates efficient pickup routes based on selected locations  
- Minimizes travel distance and fuel consumption  

#### Geocoding API
- Converts addresses into geographic coordinates  
- Helps in mapping user locations for routing  

#### Reverse Geocoding API
- Converts geographic coordinates into readable addresses  
- Used to present route and pickup information clearly  

### Gemini and Antigravity
- Used for AI-assisted development and integration  
- Supports intelligent workflows and experimentation  

### Google Cloud Platform (GCP)
- Used for deployment and scalability  
- Hosts backend services and APIs  
- Ensures reliable and scalable infrastructure  
---

## Screenshot

### Dashboard
![Dashboard](./Dashboard)

### Add User
![Add User](./Add_User)

### Log Weight  (This UI is implemented for demonstrating the API endpoint. Actually weight is logged from the embedded system directly to API endpoint as mentioned in system workflow)
![Log Weight](./Log_Weight)
---
## Demo Video
[Click here](https://drive.google.com/drive/folders/1XpPrIhoDGzViLRZeDMtkvta43oHBMqJu?usp=sharing)
It requires a minimum of 5 weight logs for the pickup prediction model (TimesFM) to start infering.

---
## Installation steps
We deployed this web app on google cloud platform. The link is provided below.
[Click here to visit the deployed dashboard](https://pickup-optimizer-411022110878.us-central1.run.app/dashboard/index.html)

There is limitation to run this locally as the app uses bigquery to run TimesFM. Also, the judges adviced us it is okay to just provide the link due to this reason.


