function getGrade(score) 
{
  if (score = 100 ) 
  {
      let grade = "+A"; 
      console.log(grade);
  }
    else if (score >= 90 && score < 100)
    {
      grade = "A";
      console.log(grade);
      
    }

    else if (score >= 89 && score > 80) 
    {
      grade = "B"; 
      console.log(grade);
    }

    else if (score >= 79 && score > 70)
    {
      grade = "C";
      console.log(grade);
    }

    else if (score >= 69 && score > 60)
    {
      grade = "D";
      console.log(grade);

    }

    else if (score >= 50 && score > 0) 
    {
      grade = "F"; 
      console.log(grade); 
    }

}
