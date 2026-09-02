namespace AssessmentScoring.Models;

public record Question(string Id, string CorrectAnswer);

public record AssessmentSection(
    string Id,
    string Name,
    double Weight,
    Dictionary<string, string> Questions);

public record Assessment(string Id, string Name, List<AssessmentSection> Sections);

public record SubmissionRequest(string? StudentId, Dictionary<string, string>? Answers);

public record SectionScore(
    string Id,
    string Name,
    int PointsEarned,
    int PointsPossible,
    double Percentage,
    bool Passed);

public record ScoreResult(
    List<SectionScore> SectionScores,
    double OverallPercentage,
    bool Passed);

public record Submission(
    string Id,
    string StudentId,
    string AssessmentId,
    List<SectionScore> SectionScores,
    double OverallPercentage,
    bool Passed);

public record ClassPerformanceResponse(
    string ClassId,
    string ClassName,
    string TeacherName,
    List<StudentPerformanceRecord> Students
);

public record StudentPerformanceRecord(
    StudentSummary Student,
    Dictionary<string, Submission?> Assessments
);

public record StudentSummary(string Id, string Name);

public record ClassSummary(string Id, string Name);

public record ClassRecord(string Id, string Name, string TeacherName, List<StudentSummary> Students);

public record AssessmentSummary(string Id, string Name);

public record SectionSummary(string Id, string Name, double Weight);

public record AssessmentDetailRecord(string Id, string Name, List<SectionSummary> Sections);
