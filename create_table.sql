CREATE TABLE IF NOT EXISTS public.attempts (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    datetime TIMESTAMP NOT NULL,
    question TEXT NOT NULL,
    is_answer_correct BOOLEAN NOT NULL,
    incorrect_answer TEXT,
    correct_answer TEXT NOT NULL
);

ALTER TABLE public.attempts ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
    BEGIN
        CREATE POLICY "Allow anonymous select" ON public.attempts FOR SELECT USING (true);
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;
    
    BEGIN
        CREATE POLICY "Allow anonymous insert" ON public.attempts FOR INSERT WITH CHECK (true);
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;
END $$;