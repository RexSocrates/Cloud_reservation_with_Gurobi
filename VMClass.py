# -*- coding: utf-8 -*-
"""
Created on Wed Jul 17 14:48:46 2019

@author: Socrates
"""

class VMClass :
    def __init__(self, insType, upfront, resMonthlyCharge, onDemandHourlyCharge, reservationLength, performance) :
        self.insType = insType
        self.upfront = upfront
        self.resHourlyCharge = resMonthlyCharge / (24 * 30)
        self.onDemandHourlyCharge = onDemandHourlyCharge
        self.reservationLength = reservationLength
        self.performance = performance