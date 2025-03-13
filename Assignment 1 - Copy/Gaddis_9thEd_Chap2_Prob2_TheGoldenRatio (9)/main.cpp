/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/cppFiles/main.cc to edit this template
 */

/*
 * File:   main.cpp
 * Author: David
 *
 * Created on February 19, 2025, 11:05 PM
 */

#include <cstdlib>
#include <iostream>

using namespace std;

/*
 *
 */
int main(int argc, char **argv)
{

    // initializing the line variables
    int ttlLine = 1050;  // Total Lines
    float cLines = 0.36; // Comment Lines

    // Calculations

    // Lines with comments variable
    int lineWC = ttlLine * cLines;

    // Lines without comments variable
    int lineWOC = ttlLine - lineWC;

    // Displaying the information.
    cout << "Lines without comments: " << lineWOC << endl;
    cout << "Total Lines: " << ttlLine << endl;
    return 0;
}
