import csv
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from skyfield.api import load
from skyfield.sgp4lib import EarthSatellite

from satellite import Satellite


# Function to calculate mean altitude
def mean_altitude(sat):
    mu = 398600.4418  # Earth's gravitational parameter (km^3/s^2)
    earth_radius_km = 6371  # Mean radius of the Earth in kilometers
    mean_motion = sat.model.no_kozai  # Revolutions per day
    semi_major_axis = (mu / (mean_motion * (2 * np.pi / 86400)) ** 2) ** (1 / 3)
    return semi_major_axis - earth_radius_km


def calculate_maneuverability(sat):
    # Calculate mean altitude
    mean_altitude_val = mean_altitude(sat)

    # Classify the orbit
    if mean_altitude_val <= 2000:
        maneuverability_score = 30
    elif 2000 < mean_altitude_val <= 35786:
        maneuverability_score = 50
    else:
        maneuverability_score = 70

    # Adjust score based on eccentricity and inclination
    ecc = sat.model.ecco
    incl = sat.model.inclo

    if ecc > 0.1:
        maneuverability_score += 10
    if incl > 45:
        maneuverability_score += 10

    return min(100, maneuverability_score)  # Ensure score doesn't exceed 100


def get_risk_category(risk_value):
    # Define the membership functions for each risk category
    very_high = fuzz.trimf(np.arange(0, 100, 1), [0, 0, 25])
    high = fuzz.trimf(np.arange(0, 100, 1), [0, 25, 50])
    medium = fuzz.trimf(np.arange(0, 100, 1), [25, 50, 75])
    low = fuzz.trimf(np.arange(0, 100, 1), [50, 75, 100])

    # Calculate the degree of membership for each category
    very_high_degree = fuzz.interp_membership(np.arange(0, 100, 1), very_high, risk_value)
    high_degree = fuzz.interp_membership(np.arange(0, 100, 1), high, risk_value)
    medium_degree = fuzz.interp_membership(np.arange(0, 100, 1), medium, risk_value)
    low_degree = fuzz.interp_membership(np.arange(0, 100, 1), low, risk_value)

    # Create a dictionary of category names and their degrees
    categories = {
        "Very High": very_high_degree,
        "High": high_degree,
        "Medium": medium_degree,
        "Low": low_degree
    }

    print(categories)
    # Find the category with the highest degree of membership
    max_category = max(categories, key=categories.get)

    return max_category, categories[max_category] * 100  # Return the category and its percentage


def calculate_orbital_similarity(sat1, sat2, altitude_threshold=1000):  # altitude_threshold in kilometers
    # Constants
    mu = 398600.4418  # Earth's gravitational parameter (km^3/s^2)
    earth_radius_km = 6371  # Mean radius of the Earth in kilometers

    # Calculate mean altitudes for both satellites
    mean_altitude_sat1 = mean_altitude(sat1)
    mean_altitude_sat2 = mean_altitude(sat2)

    # Check if the difference in mean altitude is too large
    if abs(mean_altitude_sat1 - mean_altitude_sat2) > altitude_threshold:
        return 0  # Consider orbital similarity to be 0 if altitude difference is too large

    # Existing similarity calculation code...
    # (Extract key orbital elements and calculate differences)

    # Determine similarity
    incl1, raan1, ecc1, argp1 = sat1.model.inclo, sat1.model.nodeo, sat1.model.ecco, sat1.model.argpo
    incl2, raan2, ecc2, argp2 = sat2.model.inclo, sat2.model.nodeo, sat2.model.ecco, sat2.model.argpo

    diff_incl = abs(incl1 - incl2)
    diff_raan = abs(raan1 - raan2)
    diff_ecc = abs(ecc1 - ecc2)
    diff_argp = abs(argp1 - argp2)

    similarity = 1 - (diff_incl / 180 + diff_raan / 360 + diff_ecc + diff_argp / 360) / 4
    return max(0, min(similarity, 1))  # Ensure the result is between 0 and 1

# Placeholder function for your collision calculation logic
def calculate_collision_chance(norad_id1, norad_id2, date):
    # Initialize Satellites
    sat1 = Satellite(norad_id1)
    sat2 = Satellite(norad_id2)

    # Load TLE data
    ts = load.timescale()
    satellite1 = sat1.get_tle_data()
    satellite2 = sat2.get_tle_data()

    sat1_tle_line1 = '1 13777U 83004A   20028.88653061 -.00000112 +00000-0 -46267-4 0  9994'
    sat1_tle_line2 = '2 13777 098.9546 214.5008 0017548 291.7607 068.1690 14.00452411560031'
    sat2_tle_line1 = '1  2828U 67053C   20028.83195262 -.00000031 +00000-0 +16279-4 0  9993'
    sat2_tle_line2 = '2  2828 069.9718 027.7275 0010105 305.9033 054.1135 13.97443552682482'
    #
    satellite1 = EarthSatellite(sat1_tle_line1, sat1_tle_line2, name='Satellite 1')
    satellite2 = EarthSatellite(sat2_tle_line1, sat2_tle_line2, name='Satellite 2')

    # Define Fuzzy Logic Sets and Rules
    distance = ctrl.Antecedent(np.arange(0, 10000, 1), 'distance')
    risk = ctrl.Consequent(np.arange(0, 100, 1), 'risk')
    relative_velocity = ctrl.Antecedent(np.arange(0, 15000, 1), 'relative_velocity')
    orbital_similarity = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'orbital_similarity')
    maneuverability = ctrl.Antecedent(np.arange(0, 100, 1), 'maneuverability')

    # Define risk categories
    risk['very_high'] = fuzz.trimf(risk.universe, [0, 0, 25])
    risk['high'] = fuzz.trimf(risk.universe, [0, 25, 50])
    risk['medium'] = fuzz.trimf(risk.universe, [25, 50, 75])
    risk['low'] = fuzz.trimf(risk.universe, [50, 75, 100])

    # Distance Membership Functions
    # Releax the constains(check notes for values)
    distance['very_close'] = fuzz.trimf(distance.universe, [0, 0, 150])  # e.g., 0-150 km
    distance['close'] = fuzz.trimf(distance.universe, [100, 250, 500])  # e.g., 100-500 km
    distance['moderate'] = fuzz.trimf(distance.universe, [400, 1000, 3000])  # e.g., 400-3000 km
    distance['far'] = fuzz.trimf(distance.universe, [2500, 5000, 10000])  # e.g., 2500-10000 km

    # Relative Velocity Membership Functions
    relative_velocity['slow'] = fuzz.trimf(relative_velocity.universe,
                                           [0, 0, 2])  # Up to 2 km/s, typical for close orbits
    relative_velocity['moderate'] = fuzz.trimf(relative_velocity.universe,
                                               [1, 4, 7])  # 1 to 7 km/s, covering a broad range
    relative_velocity['fast'] = fuzz.trimf(relative_velocity.universe,
                                           [5, 10, 15])  # Above 5 km/s, for high relative velocities

    # Orbital Similarity Membership Functions
    orbital_similarity['different'] = fuzz.trimf(orbital_similarity.universe, [0, 0, 0.5])
    orbital_similarity['similar'] = fuzz.trimf(orbital_similarity.universe, [0.5, 1, 1])

    # Maneuverability Membership Functions
    maneuverability['low'] = fuzz.trimf(maneuverability.universe, [0, 0, 30])
    maneuverability['medium'] = fuzz.trimf(maneuverability.universe, [20, 50, 80])
    maneuverability['high'] = fuzz.trimf(maneuverability.universe, [60, 100, 100])

    # Define Rules
    rule1 = ctrl.Rule(distance['very_close'], risk['very_high'])
    rule2 = ctrl.Rule(distance['close'], risk['high'])
    rule3 = ctrl.Rule(distance['moderate'], risk['medium'])
    rule4 = ctrl.Rule(distance['far'], risk['low'])
    rule5 = ctrl.Rule(
        relative_velocity['fast'] & distance['close'] & (orbital_similarity['similar'] | maneuverability['low']),
        risk['very_high'])
    rule6 = ctrl.Rule(distance['close'] & relative_velocity['fast'], risk['high'])
    rule7 = ctrl.Rule(maneuverability['high'] & distance['moderate'] & relative_velocity['moderate'], risk['low'])

    # Initialize Fuzzy Control System
    collision_risk_control = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6, rule7])
    collision_risk = ctrl.ControlSystemSimulation(collision_risk_control)

    year, month, day = map(int, date.split('-'))
    ts = load.timescale()
    with open(f'collision_risk_results_{norad_id1}_{norad_id2}.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        # Write the header
        writer.writerow(['Time', 'Degree of Membership to This Category', 'Membership Category', 'Distance', "Relative velocity", "Orbital Similarity", "Maneuverability"])
        # Simulation over time, every 1 minutes for 1 day
        for t in range(0, 86400, 10):  # Loop in 10-second intervals for 1 day (86400 seconds)
            hour = t // 3600
            minute = (t % 3600) // 60
            second = t % 60
            current_time = ts.utc(year, month, day, hour, minute, second)
            # Get position for each satellite
            sat1_position = satellite1.at(current_time).position.km
            sat2_position = satellite2.at(current_time).position.km

            # Calculate distance
            distance_value = np.linalg.norm(sat1_position - sat2_position)

            # Calculate relative velocity
            sat1_velocity = satellite1.at(current_time).velocity.km_per_s
            sat2_velocity = satellite2.at(current_time).velocity.km_per_s
            rel_vel_value = np.linalg.norm(sat1_velocity - sat2_velocity)

            # Calculate orbital similarity
            similarity_value = calculate_orbital_similarity(satellite1, satellite2)

            # Calculate maneuverability for each satellite
            maneuverability_sat1 = calculate_maneuverability(satellite1)
            maneuverability_sat2 = calculate_maneuverability(satellite2)
            average_maneuverability = (maneuverability_sat1 + maneuverability_sat2) / 2

            print("Distance: ", distance_value)

            collision_risk.input['distance'] = distance_value
            collision_risk.input['relative_velocity'] = rel_vel_value
            collision_risk.input['orbital_similarity'] = similarity_value
            collision_risk.input['maneuverability'] = average_maneuverability

            collision_risk.compute()

            risk_category, risk_percentage = get_risk_category(collision_risk.output['risk'])

            # Write a row for each result
            writer.writerow([current_time.utc_strftime('%Y-%m-%d %H:%M:%S UTC'), risk_percentage, risk_category, distance_value, rel_vel_value, similarity_value, average_maneuverability])


        return f"Results saved to collision_risk_results_{norad_id1}_{norad_id2}.csv"


# Function to handle the calculate button click
def on_calculate():
    # Get values from the UI
    norad_id1 = norad_id1_entry.get()
    norad_id2 = norad_id2_entry.get()
    date_str = date_entry.get()

    # Validate inputs (basic validation here, consider improving)
    if not (norad_id1_entry and norad_id2_entry and date_str):
        messagebox.showerror("Error", "All fields are required!")
        return

    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
        return

    # Here you would call your collision chance calculation function
    result = calculate_collision_chance(int(norad_id1), int(norad_id2), date_str)

    # Display the result
    result_label.config(text=str(result))

if __name__ == "__main__":
    # Set up the Tkinter window
    window = tk.Tk()
    window.title("Satellite Collision Chance Calculator")

    # Create input fields and labels
    tk.Label(window, text="Norad ID of Satellite 1:").grid(row=0, column=0, sticky="w")
    norad_id1_entry = ctk.CTkEntry(window)
    norad_id1_entry.grid(row=0, column=1)

    tk.Label(window, text="Norad ID of Satellite 2:").grid(row=1, column=0, sticky="w")
    norad_id2_entry = ctk.CTkEntry(window)
    norad_id2_entry.grid(row=1, column=1)


    tk.Label(window, text="Date (YYYY-MM-DD):").grid(row=4, column=0, sticky="w")
    date_entry = ctk.CTkEntry(window)
    date_entry.grid(row=4, column=1)

    # Calculate button
    calculate_button = ctk.CTkButton(window, text="Calculate Collision Chance", command=on_calculate)
    calculate_button.grid(row=5, column=0, columnspan=2)

    # Label to display results
    result_label = tk.Label(window, text="")
    result_label.grid(row=6, column=0, columnspan=2)

    # Run the Tkinter event loop
    window.mainloop()