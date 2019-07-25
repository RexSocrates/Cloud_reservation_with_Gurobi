# -*- coding: utf-8 -*-
"""
Created on Wed Jul 17 12:57:21 2019

@author: Socrates
"""

from gurobipy import *
from VMClass import *
import random

# generate the demand
demandLength = 24*365
# demandList = [15, 14, 18, 14, 12, 15, 17, 20, 11, 12, 19, 15, 10, 14, 11, 14, 11, 19, 13, 17, 17, 17, 19, 16]
demandList = [random.randint(10, 20) for _ in range(0, demandLength)]

# VM Class : VM type, upfrontFee, reservation hourly fee, on-demand hourly fee, reservation length, computing performance
# define the VM types and configure the reservation contracts data including upfront fee monthly fee and on-demand fee
type0 = VMClass("t3.nano_noUpfront", 0, 3.36, 0.0068, 30*24, 6)
type1 = VMClass("t3.nano_partial", 19, 1.61, 0.0068, 30*24, 6)
type2 = VMClass("t3.nano_all", 38, 0.0, 0.0068, 30*24, 6)
VM_types = [type0, type1, type2]

VM_type_name = []
for vm in VM_types :
    VM_type_name.append(vm.insType)

model = Model("heuristic_cloud_reservation")


# define a list to store the decision variables
timeList = []

reservationDecisionVars = []
reservedInstanceUtilizationDecisionVars = []
onDemandInstanceDecisionVars = []

# define a list to store the number of effective reserved instances in each stage
# initialize the list with value of zero
effectiveRI = [[]] * demandLength
# define a list to store the computing performance (not the number of VM)
computingPerformanceList = [[]] * demandLength

# define a list containing lot of dictionaries to represent the effective reserved instances in each time stage
# effectiveRI_dictList = [{insType :[] for insType in VM_type_name}] * demandLength
# computingPerformanceList_dictList = [{insType : []} for insType in VM_type_name] * demandLength


# add decision variables
for timeStage in range(0, demandLength) :
    vmTypeDecisionVarsList = []
    reservationVarInEachTimeStage = []
    utilizationVarInEachTimeStage = []
    onDemandVarInEachTimeStage = []
    for i in range(0, len(VM_types)) :
        vm = VM_types[i]
        upfrontFee = vm.upfront
        resHourlyCharge = vm.resHourlyCharge
        ondemandCharge = vm.onDemandHourlyCharge
        reservationLength = vm.reservationLength
        computingPerformance = vm.performance
        
        # add decision variables
        # initial reservation fee
        reservation = model.addVar(lb=0.0, ub=GRB.INFINITY, vtype=GRB.INTEGER)
        # the fee of launching a reserved instance
        launchedResInstance = model.addVar(lb=0.0, ub=GRB.INFINITY, vtype=GRB.INTEGER)
        # the fee of launching a on-demand instance
        ondemandInstance = model.addVar(lb=0.0, ub=GRB.INFINITY, vtype=GRB.INTEGER)
        
        # record the effective instance and the computing performance
        for currentTimeStage in range(timeStage, min(demandLength, timeStage + reservationLength-1)) :
            
            effectiveRI[currentTimeStage].append(reservation)
            computingPerformanceList[currentTimeStage].append(reservation * computingPerformance)
        
        
        # store the decision variables in a list
        utilizationVarInEachTimeStage.append(launchedResInstance)
        onDemandVarInEachTimeStage.append(ondemandInstance)

        vmTypeDecisionVarsList.append([reservation, launchedResInstance, ondemandInstance])
        
    reservedInstanceUtilizationDecisionVars.append(utilizationVarInEachTimeStage)
    onDemandInstanceDecisionVars.append(onDemandVarInEachTimeStage)
    timeList.append(vmTypeDecisionVarsList)

# define a list that represent the effective RI in each time stage
for timeStage in range(0, demandLength) :
    for i in range(0, len(VM_types)) :
        # define a var to represent the upper bound of the launched reserved instances in each time stage

model.update()

# convert to one-dimension list
# the initial reservation fee has not been added
decisionVars = []
coefficient = []

# used for that constraint that the sum of reserved and on-demand instance commputing capacities should greater than demand
vmDecisionVars = []
vmDecisionVarsCoefficient = []



for timeStageIndex in range(0, demandLength) :
    utilizationVarInEachTimeStage = reservedInstanceUtilizationDecisionVars[timeStageIndex]
    onDemandVarInEachTimeStage = onDemandInstanceDecisionVars[timeStageIndex]

    vmDecisionVarsInEachTimeStage = []
    vmDecisionVarsCoefficientInEachTimeStage = []

    for vmIndex in range(0 ,len(VM_types)) :

        # the utilization fee of each kind of instance
        vm = VM_types[vmIndex]
        reservedInstanceUtilizationFee = vm.resHourlyCharge
        onDemandFee = vm.onDemandHourlyCharge
        computingPerformance = vm.performance

        coefficient.extend([reservedInstanceUtilizationFee, onDemandFee])
        vmDecisionVarsCoefficientInEachTimeStage.append(computingPerformance)
        vmDecisionVarsCoefficientInEachTimeStage.append(computingPerformance)

        # the decision variables of each kind of instance
        vmUtilizationVar = utilizationVarInEachTimeStage[vmIndex]
        onDemandVar = onDemandVarInEachTimeStage[vmIndex]

        decisionVars.extend([vmUtilizationVar, onDemandVar])
        vmDecisionVarsInEachTimeStage.append(vmUtilizationVar)
        vmDecisionVarsInEachTimeStage.append(onDemandVar)
    
    vmDecisionVars.append(vmDecisionVarsInEachTimeStage)
    vmDecisionVarsCoefficient.append(vmDecisionVarsCoefficientInEachTimeStage)


# add objective function
model.setObjective(quicksum(coefficient[i] * decisionVars[i] for i in range(0, len(decisionVars))), GRB.MINIMIZE)

# add constraints
# non-negative constraints
for var in decisionVars :
    model.addConstr(var, GRB.GREATER_EQUAL, 0)

    
# the number of launched reserved instances cannot exceed the effective reserved instances
launchedReservedInstanceDecisionVars = []
for timeStage in range(0, len(timeList)) :
    vmTypeDecisionVarsList = timeList[timeStage]
    for vm_type_index in range(0, len(vmTypeDecisionVarsList)) :
        vm = vmTypeDecisionVarsList[vm_type_index]
        launchedReservedInstances = vm[1]
        launchedReservedInstanceDecisionVars.append(launchedReservedInstances)

    
# the sum of reserved and on-demand instances should be greater than or equal to the demand
for timeStageIndex in range(0, demandLength) :
    utilizedVmDecisionVars = vmDecisionVars[timeStageIndex]
    utilizedVmCoefficient = vmDecisionVarsCoefficient[timeStageIndex]
    model.addConstr(quicksum(utilizedVmDecisionVars[i] * utilizedVmCoefficient[i] for i in range(0, len(utilizedVmDecisionVars))), GRB.GREATER_EQUAL, demandList[timeStageIndex])


