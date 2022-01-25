# %%
from scipy.optimize import linprog
import matplotlib.pyplot as plt; plt.rcdefaults()
import numpy as np
import matplotlib.pyplot as plt

#------Functions---------
def g_function(x, y):
    if x <= y:
        return 0
    else:
        return -(x-y)

def f_function(x, y):
    if x >= y:
        return y
    else:
        return x

#*************Power Consumers*************

#------Car
car_soc = 0.7                                # Read from TeslaAPI
car_battery_capacity = 75                    # Capacity: 75kwh
car_soc_min = 0.2
car_soc_min_kwh = 0
car_discharge_level = (1 - car_soc) * car_battery_capacity

if car_soc < car_soc_min:
    car_soc_min_kwh = (car_soc_min - car_soc) * car_battery_capacity

#------Household
avg_home_consumption = 14.3                # Derived from previous data, maybe connect to TeslaAPI

#------Total Power
min_total_power_required = avg_home_consumption + car_soc_min_kwh          
max_total_power_required = avg_home_consumption + car_discharge_level

#*************Power Producers*************
#----Grid Power
grid_power = 1                      # Constant: 1[kWh]

#----Accumulator
acc_soc = 0.8                       # Read from TeslaAPI
acc_soc_min = 0.2
acc_capacity = 24.4
acc_power = acc_soc * acc_capacity
beta = 1

if acc_soc < acc_soc_min:
    acc_soc = acc_soc_min #TODO: why do I hardcode this?

#----Solar Power
amps = 9                                            # Read from SolarAPI
duration = 5                                        # Read from SolarAPI
solar_power = 230 * amps * duration * (1/1000)

#*************Linear Program Model*************

#----Coefficients 
objective_function = [grid_power, -solar_power, beta * acc_power]

#----Constraints
lhs_ineq = [[0,   0,             acc_power],                # (4.37) - Max. Accumulator Consumption [kwh]
            [0,   0,             acc_power],                # (4.38) - Min. Soc in Accumulator [kwh]
            [-1,  solar_power,   0        ],                # (4.36) - Grid Export
            [-1,  0,            -acc_power],                # (4.39) - Min. #Power demanded [kwh]
            [1,   0,             acc_power]]                # (4.40) - Max. #Power demanded [kwh] 

rhs_ineq = [(1 - acc_soc_min) * acc_capacity,               # (4.37) - Max. Accumulator Consumption [kwh]
            -(acc_soc_min * acc_capacity) + acc_power,      # (4.38) - Min. Soc in Accumulator [kwh]
            solar_power,                                    # (4.36) - Grid Export
            -min_total_power_required + solar_power,        # (4.39) - Min. #Power demanded [kwh]
            max_total_power_required - solar_power]         # (4.40) - Max. #Power demanded [kwh] 
              
#----Sign Restrictions
bnd = [(float("-inf"), float("inf")),  # Bounds of x1 --> Grid
       (0, 1),                         # Bounds of X2 --> Solar
       (0, 1)]                         # Bounds of x3 --> Accumulator
       
opt = linprog(c=objective_function, 
              A_ub=lhs_ineq, 
              b_ub=rhs_ineq, 
              bounds=bnd, 
              method="simplex")

print(opt)

#*************Visualization*************
objects = ('Grid', 'Solar', 'Accumulators')

#-----Configuration
x = np.arange(len(objects))
y1_power_producer_consumption = [opt.x[0], 
     opt.x[1] * solar_power,
     opt.x[2] * acc_power]
y2_power_producer_capacity = [0, 
               (solar_power - (opt.x[1] * solar_power)),
               (acc_power   - (opt.x[2] * acc_power))]

#-----Styling
plt.bar(x, y1_power_producer_consumption, color=['red', 'green', 'blue'], align='center',                       alpha=0.8)
plt.bar(x, y2_power_producer_capacity,    color=['grey', 'grey', 'grey'], bottom=y1_power_producer_consumption, alpha=0.5)
plt.xticks(x, objects)
plt.ylabel('Usage in [kwh]')
plt.title('Power consumption allocation [kwh]')
plt.grid(color='#95a5a6', linestyle='--', linewidth=2, axis='y', alpha=0.3)
plt.show()

#-----Logging
print("Grid Pull: ",         round( opt.x[0], 2)               , "[kwh]")
print("Solar Pull: ",        round((opt.x[1] * solar_power), 2), "[kwh] from", round(solar_power, 2), "[kwh]")
print("Accumulators Pull: ", round((opt.x[2] * acc_power  ), 2), "[kwh] from", round(acc_power, 2), "[kwh]")

print("----------------------")

print("Accumulator Level Before Discharge:", acc_power, "[kwh]")
print("Accumulator Level After Discharge:", round((acc_power - (opt.x[2] * acc_power)), 2), "[kwh]")
print("Accumulator min. reserved power: ", acc_soc_min * acc_capacity, "[kwh]")

print("----------------------")

consumed_solar_power = (opt.x[1] * solar_power)
consumed_acc_power = opt.x[2] * acc_power

excess_solar_power = solar_power * (1 - opt.x[1])
consumed_grid_power = opt.x[0]
balanced_grid_power_meter = consumed_grid_power + excess_solar_power
total_pulled_power = balanced_grid_power_meter + consumed_solar_power + consumed_acc_power
print("Reserved power for Home:", avg_home_consumption, "[kwh]")
print("Reserved power for Car:", round((total_pulled_power - avg_home_consumption), 2), "[kwh]")

print("----------------------")

print("Car SoC before:", (car_soc * 100), "%")
print("Car SoC after:",  round((car_soc + (round(total_pulled_power - avg_home_consumption, 2) / car_battery_capacity)) * 100, 2), "%")

print("----------------------")

print("Total Power Reserved for Consumption:", round(total_pulled_power, 2), "[kwh]")

print("----------------------")

print("Optimized Coefficient Values:", opt.x)

# %%
