-- Create attempts table in the api schema
CREATE TABLE IF NOT EXISTS api.attempts (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    uid TEXT NOT NULL,
    datetime TIMESTAMP NOT NULL,
    question TEXT NOT NULL,
    is_answer_correct BOOLEAN NOT NULL,
    incorrect_answer TEXT,
    correct_answer TEXT NOT NULL,
    "order" INTEGER
);

-- Set up RLS policies for the table
ALTER TABLE api.attempts ENABLE ROW LEVEL SECURITY;

-- Create policies for SELECT and INSERT operations
DO $$ 
BEGIN
    BEGIN
        CREATE POLICY "Allow anonymous select" ON api.attempts FOR SELECT USING (true);
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;
    
    BEGIN
        CREATE POLICY "Allow anonymous insert" ON api.attempts FOR INSERT WITH CHECK (true);
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;
END $$;