/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/cppFiles/main.cc to edit this template
 */

/* 
 * File:   main.cpp
 * Author: David
 *
 * Created on February 22, 2025, 3:16 PM
 */

#include <cstdlib>
#include <iostream>

using namespace std;

/*
 * 
 */
int main(int argc, char** argv) {
   
// init & define variables 
    float gasTank = 20.0; // Gas Tank total
    float mpgTown = 23.5; // Miles per Gal Town 
    float mpgHway = 28.9;  // Miles Per Gal Highway
    
// Calculations 
    float mlsHway = mpgHway * gasTank; 
    float mlsTown = mpgTown * gasTank; 
    
// Display the information 
    cout << "Town Miles remaining: " <<  mlsTown << " miles." << endl; // Miles remaining for Town 
    cout << "Highway miles remaining: " << mlsHway << " miles." << endl; // Miles remaining for Highway 
    return 0;
}

