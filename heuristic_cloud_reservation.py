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
# initialize the effective VM list with a dictionary at each time stage
effectiveRI = [{insType : [] for insType in VM_type_name}] * demandLength




# add decision variables
for timeStage in range(0, demandLength) :
    vmTypeDecisionVarsList = []
    reservationVarAtEachTimeStage = []
    utilizationVarAtEachTimeStage = []
    onDemandVarAtEachTimeStage = []

    for i in range(0, len(VM_types)) :
        vm = VM_types[i]
        insTypeName = vm.insType
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
            effectiveVmDicAtCurrentTimeStage = effectiveRI[currentTimeStage]
            effectiveVmListForInstanceType = effectiveVmDicAtCurrentTimeStage[insTypeName]
            effectiveVmListForInstanceType.append(reservation)
        
        # store the decision variables in a list
        utilizationVarAtEachTimeStage.append(launchedResInstance)
        onDemandVarAtEachTimeStage.append(ondemandInstance)

        vmTypeDecisionVarsList.append([reservation, launchedResInstance, ondemandInstance])
        
    reservedInstanceUtilizationDecisionVars.append(utilizationVarAtEachTimeStage)
    onDemandInstanceDecisionVars.append(onDemandVarAtEachTimeStage)
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
    utilizationVarAtEachTimeStage = reservedInstanceUtilizationDecisionVars[timeStageIndex]
    onDemandVarAtEachTimeStage = onDemandInstanceDecisionVars[timeStageIndex]

    vmDecisionVarsAtEachTimeStage = []
    vmDecisionVarsCoefficientAtEachTimeStage = []

    for vmIndex in range(0 ,len(VM_types)) :

        # the utilization fee of each kind of instance
        vm = VM_types[vmIndex]
        reservedInstanceUtilizationFee = vm.resHourlyCharge
        onDemandFee = vm.onDemandHourlyCharge
        computingPerformance = vm.performance

        coefficient.extend([reservedInstanceUtilizationFee, onDemandFee])
        vmDecisionVarsCoefficientAtEachTimeStage.append(computingPerformance)
        vmDecisionVarsCoefficientAtEachTimeStage.append(computingPerformance)

        # the decision variables of each kind of instance
        vmUtilizationVar = utilizationVarAtEachTimeStage[vmIndex]
        onDemandVar = onDemandVarAtEachTimeStage[vmIndex]

        decisionVars.extend([vmUtilizationVar, onDemandVar])
        vmDecisionVarsAtEachTimeStage.append(vmUtilizationVar)
        vmDecisionVarsAtEachTimeStage.append(onDemandVar)
    
    vmDecisionVars.append(vmDecisionVarsAtEachTimeStage)
    vmDecisionVarsCoefficient.append(vmDecisionVarsCoefficientAtEachTimeStage)


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


