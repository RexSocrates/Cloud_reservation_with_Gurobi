# -*- coding: utf-8 -*-
"""
Created on Wed Jul 17 12:57:21 2019

@author: Socrates
"""

from gurobipy import *
from VMClass import *
import random

# generate the demand
demandLength = 5
demandList = [15, 12, 10, 13, 13]
# demandList = [random.randint(10, 20) for _ in range(0, demandLength)]

# VM Class : VM type, upfrontFee, reservation hourly fee, on-demand hourly fee, reservation length, computing performance
# define the VM types and configure the reservation contracts data including upfront fee monthly fee and on-demand fee
# type0 = VMClass("t3.nano_noUpfront", 0, 3.36, 0.0068, 30*24, 6)
# type1 = VMClass("t3.nano_partial", 19, 1.61, 0.0068, 2, 6)
# type2 = VMClass("t3.nano_all", 38, 0.0, 0.0068, 3, 6)
type2 = VMClass("t3.nano_all", 2, 0.0, 1, 3, 6)
VM_types = [type2]

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
# effectiveRI = [{insType : [] for insType in VM_type_name}] * demandLength
effectiveRI = []
for timeStageIndex in range(0, demandLength) :
    currentTimeStageDic = {insType : [] for insType in VM_type_name}
    effectiveRI.append(currentTimeStageDic)


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
        '''
        print("Time stage : ", timeStage)
        print("End time stage :", min(demandLength, timeStage + reservationLength - 1))
        '''
        
        for currentTimeStage in range(timeStage, min(demandLength, timeStage + reservationLength)) :
            currentTimeStageDic = effectiveRI[currentTimeStage]
            currentTimeStageInstanceList = currentTimeStageDic[insTypeName]
            currentTimeStageInstanceList.append(reservation)
            '''
            effectiveVmDicAtCurrentTimeStage = effectiveRI[currentTimeStage]
            effectiveVmListForInstanceType = effectiveVmDicAtCurrentTimeStage[insTypeName]
            effectiveVmListForInstanceType.append(reservation)
            '''
        
        
        
        # store the decision variables in a list
        reservationVarAtEachTimeStage.append(reservation)
        utilizationVarAtEachTimeStage.append(launchedResInstance)
        onDemandVarAtEachTimeStage.append(ondemandInstance)

        vmTypeDecisionVarsList.append([reservation, launchedResInstance, ondemandInstance])

    reservationDecisionVars.append(reservationVarAtEachTimeStage)
    reservedInstanceUtilizationDecisionVars.append(utilizationVarAtEachTimeStage)
    onDemandInstanceDecisionVars.append(onDemandVarAtEachTimeStage)
    timeList.append(vmTypeDecisionVarsList)

model.update()

# convert to one-dimension list
# the initial reservation fee has not been added
# objective function : instance cost function
# constraint 1 : non-negative integer constraint
decisionVars = []
coefficient = []

# used for that constraint that the sum of reserved and on-demand instance commputing capacities should greater than demand
# constraint 3
vmDecisionVars = []
# decision variable coefficients : computing performance of each instance type
vmDecisionVarsCoefficient = []

for timeStageIndex in range(0, demandLength) :
    reservationVarAtEachTimeStage = reservationDecisionVars[timeStageIndex]
    utilizationVarAtEachTimeStage = reservedInstanceUtilizationDecisionVars[timeStageIndex]
    onDemandVarAtEachTimeStage = onDemandInstanceDecisionVars[timeStageIndex]

    vmDecisionVarsAtEachTimeStage = []
    vmDecisionVarsCoefficientAtEachTimeStage = []

    for vmIndex in range(0 ,len(VM_types)) :

        # the utilization fee of each kind of instance
        vm = VM_types[vmIndex]
        upfrontFee = vm.upfront
        reservedInstanceUtilizationFee = vm.resHourlyCharge
        onDemandFee = vm.onDemandHourlyCharge
        computingPerformance = vm.performance

        coefficient.extend([upfrontFee, reservedInstanceUtilizationFee, onDemandFee])
        vmDecisionVarsCoefficientAtEachTimeStage.append(computingPerformance)
        vmDecisionVarsCoefficientAtEachTimeStage.append(computingPerformance)

        # the decision variables of each kind of instance
        reservationVar = reservationVarAtEachTimeStage[vmIndex]
        vmUtilizationVar = utilizationVarAtEachTimeStage[vmIndex]
        onDemandVar = onDemandVarAtEachTimeStage[vmIndex]

        decisionVars.extend([reservationVar, vmUtilizationVar, onDemandVar])
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
for timeStageIndex in range(0, demandLength) :
    effectiveVmAtEachTimeStage = effectiveRI[timeStageIndex]
    utilizationVarAtEachTimeStage = reservedInstanceUtilizationDecisionVars[timeStageIndex]

    for instanceTypeIndex in range(0, len(VM_type_name)) :
        instanceTypeName = VM_type_name[instanceTypeIndex]
        effectiveReservationVarForInstance = effectiveVmAtEachTimeStage[instanceTypeName]
        utilizationVar = utilizationVarAtEachTimeStage[instanceTypeIndex]

        model.addConstr(utilizationVar, GRB.LESS_EQUAL, quicksum(reservationVar for reservationVar in effectiveReservationVarForInstance))

    
# the sum of reserved and on-demand instances should be greater than or equal to the demand
for timeStageIndex in range(0, demandLength) :
    utilizedVmDecisionVars = vmDecisionVars[timeStageIndex]
    utilizedVmCoefficient = vmDecisionVarsCoefficient[timeStageIndex]
    model.addConstr(quicksum(utilizedVmDecisionVars[i] * utilizedVmCoefficient[i] for i in range(0, len(utilizedVmDecisionVars))), GRB.GREATER_EQUAL, demandList[timeStageIndex])

model.write("cloud_reservation.lp")


model.optimize()
print("Objective function value : ", model.objVal)