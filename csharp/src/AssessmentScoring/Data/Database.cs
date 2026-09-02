using System.Text.Json;
using AssessmentScoring.Models;
using Microsoft.Data.Sqlite;

namespace AssessmentScoring.Data;

public class Database
{
    private readonly string _connectionString;

    public Database(string connectionString)
    {
        _connectionString = connectionString;
    }

    public void InitDb()
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();

        var ddl = @"
CREATE TABLE IF NOT EXISTS assessments (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sections (
    id            TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL REFERENCES assessments(id),
    name          TEXT NOT NULL,
    weight        REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS questions (
    id             TEXT PRIMARY KEY,
    section_id     TEXT NOT NULL REFERENCES sections(id),
    correct_answer TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS students (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS classes (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    teacher_name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS class_students (
    class_id   TEXT NOT NULL REFERENCES classes(id),
    student_id TEXT NOT NULL REFERENCES students(id),
    PRIMARY KEY (class_id, student_id)
);
CREATE TABLE IF NOT EXISTS submissions (
    id                 TEXT PRIMARY KEY,
    student_id         TEXT NOT NULL,
    assessment_id      TEXT NOT NULL REFERENCES assessments(id),
    section_scores     TEXT NOT NULL,
    overall_percentage REAL NOT NULL,
    passed             INTEGER NOT NULL
);

INSERT OR IGNORE INTO assessments VALUES ('assess-001', 'Grade 3 Reading');
INSERT OR IGNORE INTO assessments VALUES ('assess-002', 'Grade 3 Math');

INSERT OR IGNORE INTO sections VALUES ('sec-001', 'assess-001', 'Vocabulary',    0.4);
INSERT OR IGNORE INTO sections VALUES ('sec-002', 'assess-001', 'Comprehension', 0.6);
INSERT OR IGNORE INTO sections VALUES ('sec-003', 'assess-002', 'Computation',   0.5);
INSERT OR IGNORE INTO sections VALUES ('sec-004', 'assess-002', 'Word Problems', 0.5);

INSERT OR IGNORE INTO questions VALUES ('q-001', 'sec-001', 'author');
INSERT OR IGNORE INTO questions VALUES ('q-002', 'sec-001', 'setting');
INSERT OR IGNORE INTO questions VALUES ('q-003', 'sec-001', 'plot');
INSERT OR IGNORE INTO questions VALUES ('q-004', 'sec-002', 'main idea');
INSERT OR IGNORE INTO questions VALUES ('q-005', 'sec-002', 'inference');
INSERT OR IGNORE INTO questions VALUES ('q-006', 'sec-002', 'evidence');
INSERT OR IGNORE INTO questions VALUES ('q-007', 'sec-002', 'summary');
INSERT OR IGNORE INTO questions VALUES ('q-008', 'sec-003', '12');
INSERT OR IGNORE INTO questions VALUES ('q-009', 'sec-003', '25');
INSERT OR IGNORE INTO questions VALUES ('q-010', 'sec-003', '144');
INSERT OR IGNORE INTO questions VALUES ('q-011', 'sec-004', '8 apples');
INSERT OR IGNORE INTO questions VALUES ('q-012', 'sec-004', '15 minutes');
INSERT OR IGNORE INTO questions VALUES ('q-013', 'sec-004', '$3.50');

INSERT OR IGNORE INTO students VALUES ('student-001', 'Maya Chen');
INSERT OR IGNORE INTO students VALUES ('student-002', 'Jordan Williams');
INSERT OR IGNORE INTO students VALUES ('student-003', 'Priya Patel');
INSERT OR IGNORE INTO students VALUES ('student-004', 'Alex Thompson');
INSERT OR IGNORE INTO students VALUES ('student-005', 'Sam Rivera');
INSERT OR IGNORE INTO students VALUES ('student-006', 'Casey Kim');
INSERT OR IGNORE INTO students VALUES ('student-007', 'Riley Johnson');
INSERT OR IGNORE INTO students VALUES ('student-008', 'Morgan Davis');
INSERT OR IGNORE INTO students VALUES ('student-009', 'Taylor Brown');
INSERT OR IGNORE INTO students VALUES ('student-010', 'Jamie Lee');

INSERT OR IGNORE INTO classes VALUES ('class-001', 'Room 12A', 'Ms. Rivera');
INSERT OR IGNORE INTO classes VALUES ('class-002', 'Room 12B', 'Mr. Chen');
INSERT OR IGNORE INTO classes VALUES ('class-003', 'Room 12C', 'Ms. Johnson');

INSERT OR IGNORE INTO class_students VALUES ('class-001', 'student-001');
INSERT OR IGNORE INTO class_students VALUES ('class-001', 'student-002');
INSERT OR IGNORE INTO class_students VALUES ('class-001', 'student-003');
INSERT OR IGNORE INTO class_students VALUES ('class-001', 'student-004');
INSERT OR IGNORE INTO class_students VALUES ('class-001', 'student-005');
INSERT OR IGNORE INTO class_students VALUES ('class-002', 'student-004');
INSERT OR IGNORE INTO class_students VALUES ('class-002', 'student-005');
INSERT OR IGNORE INTO class_students VALUES ('class-002', 'student-006');
INSERT OR IGNORE INTO class_students VALUES ('class-002', 'student-007');
INSERT OR IGNORE INTO class_students VALUES ('class-002', 'student-008');
INSERT OR IGNORE INTO class_students VALUES ('class-003', 'student-006');
INSERT OR IGNORE INTO class_students VALUES ('class-003', 'student-007');
INSERT OR IGNORE INTO class_students VALUES ('class-003', 'student-009');
INSERT OR IGNORE INTO class_students VALUES ('class-003', 'student-010');

INSERT OR IGNORE INTO submissions VALUES ('sub-001','student-001','assess-001','[{""id"":""sec-001"",""name"":""Vocabulary"",""points_earned"":3,""points_possible"":3,""percentage"":1.0,""passed"":true},{""id"":""sec-002"",""name"":""Comprehension"",""points_earned"":4,""points_possible"":4,""percentage"":1.0,""passed"":true}]',1.0,1);
INSERT OR IGNORE INTO submissions VALUES ('sub-002','student-002','assess-001','[{""id"":""sec-001"",""name"":""Vocabulary"",""points_earned"":3,""points_possible"":3,""percentage"":1.0,""passed"":true},{""id"":""sec-002"",""name"":""Comprehension"",""points_earned"":4,""points_possible"":4,""percentage"":1.0,""passed"":true}]',1.0,1);
INSERT OR IGNORE INTO submissions VALUES ('sub-003','student-003','assess-001','[{""id"":""sec-001"",""name"":""Vocabulary"",""points_earned"":3,""points_possible"":3,""percentage"":1.0,""passed"":true},{""id"":""sec-002"",""name"":""Comprehension"",""points_earned"":2,""points_possible"":4,""percentage"":0.5,""passed"":false}]',0.7,0);
INSERT OR IGNORE INTO submissions VALUES ('sub-004','student-004','assess-001','[{""id"":""sec-001"",""name"":""Vocabulary"",""points_earned"":1,""points_possible"":3,""percentage"":0.333,""passed"":false},{""id"":""sec-002"",""name"":""Comprehension"",""points_earned"":4,""points_possible"":4,""percentage"":1.0,""passed"":true}]',0.733,0);
INSERT OR IGNORE INTO submissions VALUES ('sub-005','student-006','assess-001','[{""id"":""sec-001"",""name"":""Vocabulary"",""points_earned"":2,""points_possible"":3,""percentage"":0.667,""passed"":false},{""id"":""sec-002"",""name"":""Comprehension"",""points_earned"":3,""points_possible"":4,""percentage"":0.75,""passed"":false}]',0.717,0);
INSERT OR IGNORE INTO submissions VALUES ('sub-006','student-007','assess-001','[{""id"":""sec-001"",""name"":""Vocabulary"",""points_earned"":0,""points_possible"":3,""percentage"":0.0,""passed"":false},{""id"":""sec-002"",""name"":""Comprehension"",""points_earned"":1,""points_possible"":4,""percentage"":0.25,""passed"":false}]',0.15,0);
INSERT OR IGNORE INTO submissions VALUES ('sub-007','student-009','assess-001','[{""id"":""sec-001"",""name"":""Vocabulary"",""points_earned"":3,""points_possible"":3,""percentage"":1.0,""passed"":true},{""id"":""sec-002"",""name"":""Comprehension"",""points_earned"":4,""points_possible"":4,""percentage"":1.0,""passed"":true}]',1.0,1);
INSERT OR IGNORE INTO submissions VALUES ('sub-008','student-010','assess-001','[{""id"":""sec-001"",""name"":""Vocabulary"",""points_earned"":3,""points_possible"":3,""percentage"":1.0,""passed"":true},{""id"":""sec-002"",""name"":""Comprehension"",""points_earned"":3,""points_possible"":4,""percentage"":0.75,""passed"":false}]',0.85,0);
INSERT OR IGNORE INTO submissions VALUES ('sub-009','student-001','assess-002','[{""id"":""sec-003"",""name"":""Computation"",""points_earned"":3,""points_possible"":3,""percentage"":1.0,""passed"":true},{""id"":""sec-004"",""name"":""Word Problems"",""points_earned"":3,""points_possible"":3,""percentage"":1.0,""passed"":true}]',1.0,1);
INSERT OR IGNORE INTO submissions VALUES ('sub-010','student-009','assess-002','[{""id"":""sec-003"",""name"":""Computation"",""points_earned"":2,""points_possible"":3,""percentage"":0.667,""passed"":false},{""id"":""sec-004"",""name"":""Word Problems"",""points_earned"":2,""points_possible"":3,""percentage"":0.667,""passed"":false}]',0.667,0);
";
        using var cmd = conn.CreateCommand();
        cmd.CommandText = ddl;
        cmd.ExecuteNonQuery();
    }

    public Assessment? GetAssessmentWithSections(string assessmentId)
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();

        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT id, name FROM assessments WHERE id = $id";
        cmd.Parameters.AddWithValue("$id", assessmentId);
        using var reader = cmd.ExecuteReader();
        if (!reader.Read()) return null;

        var assessment = new Assessment(reader.GetString(0), reader.GetString(1), new List<AssessmentSection>());
        reader.Close();

        using var secCmd = conn.CreateCommand();
        secCmd.CommandText = "SELECT id, name, weight FROM sections WHERE assessment_id = $aid ORDER BY id";
        secCmd.Parameters.AddWithValue("$aid", assessmentId);

        var sectionData = new List<(string Id, string Name, double Weight)>();
        using (var secReader = secCmd.ExecuteReader())
        {
            while (secReader.Read())
                sectionData.Add((secReader.GetString(0), secReader.GetString(1), secReader.GetDouble(2)));
        }

        foreach (var (secId, secName, weight) in sectionData)
        {
            var questions = new Dictionary<string, string>();
            using var qCmd = conn.CreateCommand();
            qCmd.CommandText = "SELECT id, correct_answer FROM questions WHERE section_id = $sid ORDER BY id";
            qCmd.Parameters.AddWithValue("$sid", secId);
            using var qReader = qCmd.ExecuteReader();
            while (qReader.Read())
                questions[qReader.GetString(0)] = qReader.GetString(1);

            assessment.Sections.Add(new AssessmentSection(secId, secName, weight, questions));
        }

        return assessment;
    }

    public string SaveSubmission(
        string studentId,
        string assessmentId,
        List<SectionScore> sectionScores,
        double overallPercentage,
        bool passed)
    {
        var sectionScoresJson = JsonSerializer.Serialize(sectionScores.Select(s => new
        {
            id = s.Id,
            name = s.Name,
            points_earned = s.PointsEarned,
            points_possible = s.PointsPossible,
            percentage = s.Percentage,
            passed = s.Passed,
        }));

        using var conn = new SqliteConnection(_connectionString);
        conn.Open();

        using var checkCmd = conn.CreateCommand();
        checkCmd.CommandText = "SELECT id FROM submissions WHERE student_id = $sid AND assessment_id = $aid";
        checkCmd.Parameters.AddWithValue("$sid", studentId);
        checkCmd.Parameters.AddWithValue("$aid", assessmentId);
        var existingId = checkCmd.ExecuteScalar() as string;

        if (existingId != null)
        {
            using var updateCmd = conn.CreateCommand();
            updateCmd.CommandText = @"UPDATE submissions
                SET section_scores = $scores, overall_percentage = $pct, passed = $passed
                WHERE id = $id";
            updateCmd.Parameters.AddWithValue("$scores", sectionScoresJson);
            updateCmd.Parameters.AddWithValue("$pct", overallPercentage);
            updateCmd.Parameters.AddWithValue("$passed", passed ? 1 : 0);
            updateCmd.Parameters.AddWithValue("$id", existingId);
            updateCmd.ExecuteNonQuery();
            return existingId;
        }
        else
        {
            var submissionId = $"sub-{Guid.NewGuid():N}"[..12];
            using var insertCmd = conn.CreateCommand();
            insertCmd.CommandText = @"INSERT INTO submissions
                (id, student_id, assessment_id, section_scores, overall_percentage, passed)
                VALUES ($id, $sid, $aid, $scores, $pct, $passed)";
            insertCmd.Parameters.AddWithValue("$id", submissionId);
            insertCmd.Parameters.AddWithValue("$sid", studentId);
            insertCmd.Parameters.AddWithValue("$aid", assessmentId);
            insertCmd.Parameters.AddWithValue("$scores", sectionScoresJson);
            insertCmd.Parameters.AddWithValue("$pct", overallPercentage);
            insertCmd.Parameters.AddWithValue("$passed", passed ? 1 : 0);
            insertCmd.ExecuteNonQuery();
            return submissionId;
        }
    }

    public List<Submission> GetSubmissionsForStudent(string studentId)
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();

        using var cmd = conn.CreateCommand();
        cmd.CommandText = @"
          SELECT id, student_id, assessment_id, section_scores, overall_percentage, passed
          FROM submissions WHERE student_id = $student_id";
        cmd.Parameters.AddWithValue("$student_id", studentId);

        var submissions = new List<Submission>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var sectionScores = JsonSerializer.Deserialize<List<SectionScoreJson>>(reader.GetString(3))!
                .Select(s => new SectionScore(s.id, s.name, s.points_earned, s.points_possible, s.percentage, s.passed))
                .ToList();

            submissions.Add(new Submission(
                reader.GetString(0),
                reader.GetString(1),
                reader.GetString(2),
                sectionScores,
                reader.GetDouble(4),
                reader.GetInt64(5) != 0));
        }
        return submissions;
    }

    public List<ClassSummary> GetClasses()
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT id, name FROM classes ORDER BY id";
        var classes = new List<ClassSummary>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
            classes.Add(new ClassSummary(reader.GetString(0), reader.GetString(1)));
        return classes;
    }

    public ClassPerformanceResponse? GetClassPerformanceReport(string classId)
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();

        // get class details
        using var cmdClass = new SqliteCommand("SELECT name, teacher_name FROM classes WHERE id = $classId", conn);
        cmdClass.Parameters.AddWithValue("$classId", classId);

        using var clsReader = cmdClass.ExecuteReader();
        if (!clsReader.Read()) return null;
        
        var className = clsReader.GetString(0);
        var teacherName = clsReader.GetString(1);
        clsReader.Close();

        // get assessment details
        var assessmentIds = new List<string>();
        using var cmdAssess = new SqliteCommand("SELECT id FROM assessments", conn);
        using var assessReader = cmdAssess.ExecuteReader();
        while (assessReader.Read())
        {
            assessmentIds.Add(assessReader.GetString(0));
        }
        assessReader.Close();

        // get student details
        var query = @"
            SELECT 
                s.id AS student_id, 
                s.name AS student_name,
                sub.id AS submission_id,
                sub.assessment_id,
                sub.overall_percentage,
                sub.passed,
                sub.section_scores
            FROM students s
            JOIN class_students cs ON s.id = cs.student_id
            LEFT JOIN submissions sub ON s.id = sub.student_id
            WHERE cs.class_id = $classId
            ORDER BY s.name ASC;";

        using var cmd = new SqliteCommand(query, conn);
        cmd.Parameters.AddWithValue("$classId", classId);

        var studentRecordsMap = new Dictionary<string, (string Name, Dictionary<string, Submission?> Assessments)>();

        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var studentId = reader.GetString(0);
            var studentName = reader.GetString(1);

            if (!studentRecordsMap.ContainsKey(studentId))
            {
                // Pre-populate every known assessmentId with a null value as requested
                var matrix = assessmentIds.ToDictionary(id => id, id => (Submission?)null);
                studentRecordsMap[studentId] = (studentName, matrix);
            }

            // If a submission row exists, populate the exact Submission domain model
            if (!reader.IsDBNull(2))
            {
                var submissionId = reader.GetString(2);
                var assessmentId = reader.GetString(3);
                double overallPercentage = reader.GetDouble(4);
                bool passed = reader.GetInt32(5) == 1;
                
                var sectionScores = new List<SectionScore>();
                if (!reader.IsDBNull(6))
                {
                    var rawJson = reader.GetString(6);
                    sectionScores = JsonSerializer.Deserialize<List<SectionScore>>(rawJson) ?? new();
                }

                studentRecordsMap[studentId].Assessments[assessmentId] = new Submission(
                    Id: submissionId,
                    StudentId: studentId,
                    AssessmentId: assessmentId,
                    SectionScores: sectionScores,
                    OverallPercentage: overallPercentage,
                    Passed: passed
                );
            }
        }

        var studentList = studentRecordsMap.Select(kvp => new StudentPerformanceRecord(
            Student: new StudentSummary(kvp.Key, kvp.Value.Name),
            Assessments: kvp.Value.Assessments
        )).ToList();

        return new ClassPerformanceResponse(classId, className, teacherName, studentList);
    }

    public ClassRecord? GetClassWithStudents(string classId)
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();

        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT id, name, teacher_name FROM classes WHERE id = $id";
        cmd.Parameters.AddWithValue("$id", classId);
        using var reader = cmd.ExecuteReader();
        if (!reader.Read()) return null;

        var id = reader.GetString(0);
        var name = reader.GetString(1);
        var teacherName = reader.GetString(2);
        reader.Close();

        using var studentCmd = conn.CreateCommand();
        studentCmd.CommandText = @"
SELECT s.id, s.name FROM students s
JOIN class_students cs ON s.id = cs.student_id
WHERE cs.class_id = $cid ORDER BY s.id";
        studentCmd.Parameters.AddWithValue("$cid", classId);

        var students = new List<StudentSummary>();
        using var studentReader = studentCmd.ExecuteReader();
        while (studentReader.Read())
            students.Add(new StudentSummary(studentReader.GetString(0), studentReader.GetString(1)));

        return new ClassRecord(id, name, teacherName, students);
    }

    public List<AssessmentSummary> GetAssessments()
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT id, name FROM assessments ORDER BY id";
        var assessments = new List<AssessmentSummary>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
            assessments.Add(new AssessmentSummary(reader.GetString(0), reader.GetString(1)));
        return assessments;
    }

    public AssessmentDetailRecord? GetAssessmentDetail(string assessmentId)
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();

        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT id, name FROM assessments WHERE id = $id";
        cmd.Parameters.AddWithValue("$id", assessmentId);
        using var reader = cmd.ExecuteReader();
        if (!reader.Read()) return null;

        var id = reader.GetString(0);
        var name = reader.GetString(1);
        reader.Close();

        using var secCmd = conn.CreateCommand();
        secCmd.CommandText = "SELECT id, name, weight FROM sections WHERE assessment_id = $aid ORDER BY id";
        secCmd.Parameters.AddWithValue("$aid", assessmentId);

        var sections = new List<SectionSummary>();
        using var secReader = secCmd.ExecuteReader();
        while (secReader.Read())
            sections.Add(new SectionSummary(secReader.GetString(0), secReader.GetString(1), secReader.GetDouble(2)));

        return new AssessmentDetailRecord(id, name, sections);
    }

    private record SectionScoreJson(
        string id, string name, int points_earned, int points_possible, double percentage, bool passed);
}
