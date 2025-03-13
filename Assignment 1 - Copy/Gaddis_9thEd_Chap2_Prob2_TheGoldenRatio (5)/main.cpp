/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/cppFiles/main.cc to edit this template
 */

/* 
 * File:   main.cpp
 * Author: David
 *
 * Created on February 22, 2025, 1:46 PM
 */

#include <cstdlib>
#include <iostream>

using namespace std;

/*
 * 
 */
int main(int argc, char** argv) {
    
// Init Variables 
    float riselvl = 1.5; 
    
// Calculations
    float fiveyr = 5 * riselvl;
    float sevnyr = 7 * riselvl;
    float tenyr = 10 * riselvl;
    
    
// Display information 
    
    cout << "Millimeters higher than the current level that the ocean’s level in five years: " << fiveyr << " mm" << endl; 
    cout << "Millimeters higher than the current level that the ocean’s level in seven years: " << sevnyr << " mm" << endl; 
    cout << "Millimeters higher than the current level that the ocean’s level in ten years: " << tenyr << " mm" << endl;
   

    return 0;
}

