/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/cppFiles/main.cc to edit this template
 */

/* 
 * File:   main.cpp
 * Author: David
 *
 * Created on February 18, 2025, 7:22 PM
 */

#include <cstdlib>
#include <iostream>


using namespace std;

/*
 * 
 */
int main(int argc, char** argv) {

// initializing & defining Variables 
    int recHght = 5;  // Rectangle height value 
    float gRatio = 1.62;  // Golden ratio 
    
// Calculation for width
    float recWth = recHght * gRatio; 
    
// Output 
    cout << "Your rectangle width is: " << recWth << "cm" << endl; 
    return 0;
}

