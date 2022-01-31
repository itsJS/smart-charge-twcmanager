# %%
from scipy.optimize import linprog
import matplotlib.pyplot as plt; plt.rcdefaults()
import numpy as np
import matplotlib.pyplot as plt

#------Functions---------
def g_function(x, y):
    if x <= y:
        return 0 #since there is no solar power anymore available we return 0, cause all solar power will go to charge the acc anyways
    else:
        return -(x-y)

def f_function(x, y):
    if x >= y:
        return y
    else:
        return x

#*************Power Consumers*************

#------Car
car_soc = float(input("Enter car soc:"))           # Read from TeslaAPI
car_battery_capacity = 75                   # Capacity: 75kwh
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
acc_soc = float(input("Enter acc soc:"))           # Read from TeslaAPI
acc_soc_min = 0.2
acc_capacity = 24.4
beta = 1

if acc_soc < acc_soc_min:
    # The LP optimizes while ensuring that the accumulator does not go below the 
    # user-defined acc_soc_min. The only reason for discharge below 20% is preservation 
    # reasons (not controlled by the LP) or external reasons. The optimizer can only 
    # optimize if the accumulator shows a value between 20% and 100%. The accumulator 
    # consumption is discarded if it is <=20%. The LP does not optimize if the value 
    # acc_soc < acc_soc_min, therefore we hardcode it to equate acc_soc_min and thus 
    # the LP knows that the accumulator should be discarded.
    acc_soc = acc_soc_min 
acc_power = acc_soc * acc_capacity
#----Solar Power
amps = float(input("Enter solar power amps:")) # Read from SolarAPI
duration = float(input("Enter solar power duration:")) #Bug 18 - 31  SOLVED! Automate testing # Read from SolarAPI
solar_power = 230 * amps * duration * (1/1000)

#*************Linear Program Model*************

#----Coefficients 
objective_function = [grid_power, -solar_power, beta * acc_power]

#----Constraints
lhs_ineq = [[0,   0,             acc_power],                # (4.37) : Max. Accumulator Consumption [kwh]
            [0,   0,             acc_power],                # (4.38) : Min. Soc in Accumulator [kwh] (The evaluation with f_function for acc_j happens after optimization, because it is all about how much to charge after knowing how much power is coming. And from a temporal point of view, the solar power is consumed first by house and car and THEN charged, therefore the charging needs to be accounted for after consumption)
            [-1,  solar_power,   0        ],                #  x1 >= -(solar_power * (1 - x2)) : Grid Export (The evaluation with g_function happens after optimization, because this is where we determine how much power to give to the accumulator to charge.)
            [-1,  0,            -acc_power],                # (4.39) : Min. #Power demanded [kwh]
            [1,   0,             acc_power]]                # (4.40) : Max. #Power demanded [kwh] 

rhs_ineq = [(1 - acc_soc_min) * acc_capacity,               # (4.37) : Max. Accumulator Consumption [kwh]
            -(acc_soc_min * acc_capacity) + acc_power,      # (4.38) : Min. Soc in Accumulator [kwh]
            solar_power,                                    #  x1 >= -(solar_power * (1 - x2)) : Grid Export
            -min_total_power_required + solar_power,        # (4.39) : Min. #Power demanded [kwh]
            max_total_power_required - solar_power]         # (4.40) : Max. #Power demanded [kwh] 
              
#----Sign Restrictions
bnd = [(float("-inf"), float("inf")),  # Bounds of x1 --> Grid
       (0, 1),                         # Bounds of X2 --> Solar
       (0, 1)]                         # Bounds of x3 --> Accumulator

#----Simplex Optimization
opt = linprog(c=objective_function, 
              A_ub=lhs_ineq, 
              b_ub=rhs_ineq, 
              bounds=bnd, 
              method="simplex")

#-----Post Evaluations
#-Grid - Pull stands for import(+) & export(-)
grid_pull_pre_accumulator_charge = opt.x[0] * grid_power
grid_export = g_function(solar_power * (1-opt.x[1]), (1-acc_soc) * acc_capacity)

grid_import = 0
# If no solar power remains to export to grid, that means: either we broke even with 
# charging accumulator OR we imported power from grid. That is why we check if we 
# imported from the grid through: grid_pull_pre_accumulator_charge
if grid_export == 0 and grid_pull_pre_accumulator_charge > 0:
    # needed for calculating total power consumed, as adding the 
    # grid pull when exporting power would mess up the total 
    # consumed power calculation
    grid_import = grid_pull_pre_accumulator_charge 

# needed for visualization, cause it depicts import/ export
grid_pull = grid_import + grid_export
    
#-Solar
consumed_solar_power_for_acc_charge = f_function(solar_power * (1-opt.x[1]), (1-acc_soc) * acc_capacity)
consumed_solar_power = opt.x[1] * solar_power + consumed_solar_power_for_acc_charge

#-Accumulator
consumed_acc_power = opt.x[2] * acc_power
acc_level_after_discharge = round((acc_power - consumed_acc_power), 2)
acc_level_after_charge = acc_level_after_discharge + consumed_solar_power_for_acc_charge

#-Total Consumed Power
total_pulled_power = round(grid_import + consumed_solar_power + consumed_acc_power, 2)

#*************Visualization*************
print(opt)
objects = ('Grid', 'Solar', 'Accumulators')

#-----Configuration
x = np.arange(len(objects))
y1_power_producer_consumption = [grid_pull, 
                                 consumed_solar_power,
                                 consumed_acc_power]
y2_power_producer_capacity = [0, 
                              (solar_power - consumed_solar_power),
                              (acc_power   - consumed_acc_power)]

y3_acc_charge_delta = [0, 0, (acc_level_after_charge - (acc_power - consumed_acc_power))]                            

#-----Styling
plt.bar(x, y1_power_producer_consumption, color=['red', 'green', 'blue'], align='center',                       alpha=0.8)
plt.bar(x, y2_power_producer_capacity,    color=['grey', 'grey', 'grey'], bottom=y1_power_producer_consumption, alpha=0.5)
plt.bar(x, y3_acc_charge_delta, color=['white', 'white', 'blue'], bottom= y2_power_producer_capacity, alpha=0.2)
plt.xticks(x, objects)
plt.ylabel('Usage in [kwh]')
plt.title('Power consumption allocation [kwh]')
plt.grid(color='#95a5a6', linestyle='--', linewidth=2, axis='y', alpha=0.3)
plt.show()

#-----Logging
print("----------------------")
print("** Overview **")
print("Grid Pull: ",                               round(grid_pull, 2), "[kwh]")
print("Solar Consumption: ",                       round(consumed_solar_power, 2), "[kwh] from", round(solar_power, 2), "[kwh]")
print("Accumulators Consumption: ",                round(consumed_acc_power, 2), "[kwh] from", round(acc_power, 2), "[kwh]")

print("----------------------")
print("** Accumulator **")
print("Min. power for preservation: ",          acc_soc_min * 100, "% /", acc_soc_min * acc_capacity, "[kwh]")
print("Level Before Discharge:",                round(acc_power/acc_capacity * 100, 2), "% /", acc_power, "[kwh]")
print("Level After Discharge:",                 round(acc_level_after_discharge/acc_capacity * 100, 2), "% /", acc_level_after_discharge, "[kwh]")
print("Consumed Solar Power for Charging:",     round(consumed_solar_power_for_acc_charge, 2), "[kwh]")
print("Level After Charging from Solar Power:", round(acc_level_after_charge/acc_capacity * 100, 2), "% /", acc_level_after_charge, "[kwh]")

print("----------------------")
print("** Home **")
print("Consumed Power:", avg_home_consumption, "[kwh]")

print("----------------------")
print("** E-Car **")
print("Consumed Power:",  round((total_pulled_power - avg_home_consumption - consumed_solar_power_for_acc_charge), 2), "[kwh]")
print("SoC before:", (car_soc * 100), "%")
print("SoC after:",  round((car_soc + (round(total_pulled_power - avg_home_consumption - consumed_solar_power_for_acc_charge, 2) / car_battery_capacity)) * 100, 2), "%")

print("----------------------")

print("Total Power Reserved for Consumption:", round(total_pulled_power, 2), "[kwh]")
print("----------------------")
print("Smart Utility Meter:", round(grid_pull, 2), "[kwh]")
print("----------------------")

print("Optimized Coefficient Values:", opt.x)
# %%

# %%
