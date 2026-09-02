using AssessmentScoring.Models;

namespace AssessmentScoring.Services;

public class ScoringService
{
    /// <summary>
    /// Score a student's submitted answers across a sectioned assessment.
    ///
    /// Each section has a weight and its own set of questions. The student must
    /// meet the mastery threshold both overall (weighted) and in each section
    /// individually to pass.
    /// </summary>
    /// <param name="submittedAnswers">Maps question ID to the student's answer string.</param>
    /// <param name="sections">
    ///   List of sections, each with Id, Name, Weight, and Questions (dict of questionId to correctAnswer).
    /// </param>
    /// <returns>
    ///   ScoreResult containing per-section scores, overall weighted percentage, and passed flag.
    ///   Passed is true only if overall_percentage >= MasteryThreshold AND every section passed.
    /// </returns>
    /// <remarks>
    /// Rules:
    ///   - Unanswered questions count as incorrect
    ///   - Extra answers not in any section are ignored
    ///   - Comparison is case-insensitive
    ///   - An empty submission is valid and scores 0
    ///   - Section weights are guaranteed to sum to 1.0
    ///
    /// TODO: Implement this method.
    /// The tests in ScoringTests.cs define the expected behavior.
    /// Run: docker compose run test --filter "Category=Scoring"
    /// </remarks>
    public ScoreResult Calculate(
        Dictionary<string, string> submittedAnswers,
        List<AssessmentSection> sections)
    {
      // returns
      var sectionScores = new List<SectionScore>();
      double percentageOverall = 0.0;
      bool allSectionsPassed = true; 

      foreach (AssessmentSection section in sections) // move content to helper function? 
      {
        // score per section
        int score = 0;

        foreach (var question in section.Questions)
        {
          string id = question.Key;
          string answer = question.Value;

          // did the student answer and did they get it right
          if (submittedAnswers.TryGetValue(id, out string? submittedAnswer) && answer == submittedAnswer)
          {
            score++; 
          }
          
        }

        // calculate percentage correct and if student passed
        double percentage = (double)score / section.Questions.Count;
        bool passed = percentage >= Config.MasteryThreshold;

        if (!passed)
        {
          allSectionsPassed = false; 
        }
        
        // add official section score
        sectionScores.Add(new SectionScore(
          section.Id,
          section.Name,
          score,
          section.Questions.Count,
          percentage,
          passed
        ));

        // tally overall grade
        percentageOverall += percentage * section.Weight;
      }

      bool passedOverall = percentageOverall >= Config.MasteryThreshold && allSectionsPassed;
      return new ScoreResult(sectionScores, percentageOverall, passedOverall); 
    }
}
