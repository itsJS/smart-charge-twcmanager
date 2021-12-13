# %%
from scipy.optimize import linprog
import matplotlib.pyplot as plt; plt.rcdefaults()
import numpy as np
import matplotlib.pyplot as plt

#------Global Vars---------
min_total_power_required = 29.3
max_total_power_required = 89.3


#-------Powerwall----------
powerwalls_soc = 0.8                       # Read from TeslaAPI
if powerwalls_soc < 0.2:
    powerwalls_soc = 0.2
powerwall_power = powerwalls_soc * 24.4


#-------Solar Panels----------
amps = 9        # Read from SolarAPI
duration = 24    # Read from SolarAPI

beta_is_sunny = 1
if amps >= 5:
    beta_is_sunny = 1
else: 
    beta_is_sunny = 0

solar_power = beta_is_sunny * 220 * amps * duration * (1/1000)

#-------Linear Program----------
# Coefficients for x_i, respectively where i = 1..3 ==> x1 - (beta*220*a*d*x2) + powerwalls_soc*x3
objective_function = [1, -solar_power, powerwall_power]

lhs_ineq = [[0, 0, powerwall_power],                # Max. Powerwall Consumption [kwh]
            [0, 0, powerwall_power],                # Min. Soc in Powerwall
            [-1, solar_power, 0],                   # Einspeisen
            [-1, -solar_power, -powerwall_power],   # Min. Supplied Total Power in [kwh]
            [1, solar_power, powerwall_power]]      # Max. Supplied Total Power in [kwh]

rhs_ineq = [19.52,                   # Max. Powerwall Consumption [kwh]
            -4.88+powerwall_power,   # Min. Soc in Powerwall
            solar_power,             # Einspeisen
            -min_total_power_required,        # Min. Supplied Total Power [kwh]
            max_total_power_required]         # Max. Supplied Total Power Worst Case [kwh] -- this no. will change based on the amount of power we need.
              

bnd = [(float("-inf"), float("inf")),  # Bounds of x1 --> Grid
       (0, 1),                         # Bounds of X2 --> Solar
       (0, 1)]                         # Bounds of x3 --> Powerwall
       
opt = linprog(c=objective_function, 
              A_ub=lhs_ineq, 
              b_ub=rhs_ineq, 
              bounds=bnd, 
              method="simplex")

print(opt)

#-------Visualization----------
objects = ('Grid', 'Solar', 'Powerwalls')
y_pos = np.arange(len(objects))
performance = [opt.x[0], 
               opt.x[1] * solar_power,
               opt.x[2] * powerwall_power]

plt.bar(y_pos, performance, color=['red', 'green', 'blue'], align='center', alpha=0.5)
plt.xticks(y_pos, objects)
plt.ylabel('Usage in [kwh]')
plt.title('Power consumption allocation [kwh]')

plt.show()

print("Grid Pull: ", round(opt.x[0],2), "[kwh]")
print("Solar Pull: ", round((opt.x[1] * solar_power),2), "[kwh] from", round(solar_power,2), "[kwh]")
print("Powerwalls Pull: ", round((opt.x[2] * powerwall_power),2), "[kwh] from", round(powerwall_power,2), "[kwh]")
total_pulled_power = opt.x[0] + (opt.x[1] * solar_power) + opt.x[2] * powerwall_power
print("Total:", round(total_pulled_power,2), "[kwh]")
print("Optimized Coefficient Values:", opt.x)



# %%
