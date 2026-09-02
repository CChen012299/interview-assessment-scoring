using AssessmentScoring.Data;
using AssessmentScoring.Models;
using AssessmentScoring.Services;

namespace AssessmentScoring.Controllers;

public static class AssessmentController
{
    public static void MapRoutes(WebApplication app)
    {
        app.MapPost("/assessments/{assessmentId}/submit", Submit);
        app.MapGet("/students/{studentId}/scores", GetScores);
        app.MapGet("/classes", GetClasses);
        app.MapGet("/classes/{classId}", GetClass);
        app.MapGet("/classes/{classId}/performance", GetClassPerformance);
        app.MapGet("/assessments", GetAssessments);
        app.MapGet("/assessments/{assessmentId}", GetAssessment);
    }

    private static IResult Submit(
        string assessmentId,
        SubmissionRequest body,
        Database db,
        ScoringService scorer)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(body.StudentId))
                return Results.UnprocessableEntity();

            var assessment = db.GetAssessmentWithSections(assessmentId);
            if (assessment is null)
                return Results.Json(new { detail = "Assessment not found" }, statusCode: 404);

            var result = scorer.Calculate(body.Answers ?? new Dictionary<string, string>(), assessment.Sections);

            var submissionId = db.SaveSubmission(
                studentId: body.StudentId,
                assessmentId: assessmentId,
                sectionScores: result.SectionScores,
                overallPercentage: result.OverallPercentage,
                passed: result.Passed);

            return Results.Ok(new
            {
                submission_id = submissionId,
                student_id = body.StudentId,
                assessment_id = assessmentId,
                section_scores = result.SectionScores.Select(s => new
                {
                    id = s.Id,
                    name = s.Name,
                    points_earned = s.PointsEarned,
                    points_possible = s.PointsPossible,
                    percentage = s.Percentage,
                    passed = s.Passed,
                }),
                overall_percentage = result.OverallPercentage,
                passed = result.Passed,
            });
        }
        catch (Exception ex)
        {
            return Results.Json(new { error = ex.Message }, statusCode: 500);
        }
    }

    private static IResult GetScores(string studentId, Database db)
    {
        var submissions = db.GetSubmissionsForStudent(studentId);
        return Results.Ok(submissions.Select(s => new
        {
            submission_id = s.Id,
            student_id = s.StudentId,
            assessment_id = s.AssessmentId,
            section_scores = s.SectionScores.Select(sc => new
            {
                id = sc.Id,
                name = sc.Name,
                points_earned = sc.PointsEarned,
                points_possible = sc.PointsPossible,
                percentage = sc.Percentage,
                passed = sc.Passed,
            }),
            overall_percentage = s.OverallPercentage,
            passed = s.Passed,
        }));
    }

    private static IResult GetClasses(Database db)
    {
        return Results.Ok(db.GetClasses());
    }


    private static IResult GetClass(string classId, Database db)
    {
        var result = db.GetClassWithStudents(classId);
        if (result is null)
            return Results.Json(new { detail = "Class not found" }, statusCode: 404);
        return Results.Ok(result);
    }

    private static IResult GetClassPerformance(string classId, Database db)
    {
        var report = db.GetClassPerformanceReport(classId);
        if (report is null)
        {
            return Results.Json(new { detail = "Class not found" }, statusCode: 404);
        }

        return Results.Ok(report);
    }

    private static IResult GetAssessments(Database db)
    {
        return Results.Ok(db.GetAssessments());
    }

    private static IResult GetAssessment(string assessmentId, Database db)
    {
        var result = db.GetAssessmentDetail(assessmentId);
        if (result is null)
            return Results.Json(new { detail = "Assessment not found" }, statusCode: 404);
        return Results.Ok(result);
    }
}
