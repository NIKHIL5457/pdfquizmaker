import os
import re
import json
import random
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'pdfquizsecret123'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['GENERATED_FOLDER'] = 'generated'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        print(f"Error extracting text: {e}")
    return text

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\.\,\?\:\;\!\-]', '', text)
    return text.strip()

def extract_sentences(text):
    """Extract clean sentences from text"""
    sentences = re.split(r'[.!?]+', text)
    clean_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 20 and len(sentence.split()) > 5:
            if sentence[0].isupper():
                clean_sentences.append(sentence)
    
    return clean_sentences

def extract_definitions(sentences):
    """Extract definition sentences"""
    definitions = []
    for sentence in sentences:
        if any(x in sentence.lower() for x in [' is a ', ' is an ', ' are a ', ' are an ', ' refers to ', ' defined as ']):
            definitions.append(sentence)
    return definitions

def extract_facts_with_dates(sentences):
    """Extract sentences with dates"""
    dated_facts = []
    for sentence in sentences:
        if re.search(r'\b(19|20)\d{2}\b', sentence):
            dated_facts.append(sentence)
    return dated_facts

def extract_composition_facts(sentences):
    """Extract sentences about composition"""
    composition = []
    for sentence in sentences:
        if any(x in sentence.lower() for x in [' contains ', ' consists of ', ' comprises ', ' includes ']):
            composition.append(sentence)
    return composition

def extract_function_facts(sentences):
    """Extract sentences about function/purpose"""
    functions = []
    for sentence in sentences:
        if any(x in sentence.lower() for x in [' is used ', ' are used ', ' enables ', ' allows ', ' provides ', ' supports ']):
            functions.append(sentence)
    return functions

def generate_mcq_definition(sentence, index, all_sentences):
    """Generate MCQ from definition sentence"""
    
    # Extract term and definition
    if ' is a ' in sentence.lower():
        parts = sentence.split(' is a ', 1)
        term = parts[0].strip()
        definition = 'is a ' + parts[1].strip()
    elif ' is an ' in sentence.lower():
        parts = sentence.split(' is an ', 1)
        term = parts[0].strip()
        definition = 'is an ' + parts[1].strip()
    elif ' are a ' in sentence.lower():
        parts = sentence.split(' are a ', 1)
        term = parts[0].strip()
        definition = 'are a ' + parts[1].strip()
    elif ' are an ' in sentence.lower():
        parts = sentence.split(' are an ', 1)
        term = parts[0].strip()
        definition = 'are an ' + parts[1].strip()
    else:
        return None
    
    # Clean term
    term = term.strip()
    if len(term.split()) > 2:
        term = ' '.join(term.split()[-2:])
    
    # Clean definition
    definition = definition.split('.')[0].strip()
    if len(definition) > 60:
        definition = definition[:57] + "..."
    
    # Create MCQ
    question = f"What is {term}?"
    correct_answer = definition
    
    # Generate wrong answers
    distractors = []
    
    # Get other definitions as wrong answers
    other_defs = []
    for s in all_sentences[:20]:
        if s != sentence and any(x in s.lower() for x in [' is a ', ' is an ', ' are a ', ' are an ']):
            if ' is a ' in s.lower():
                d = 'is a ' + s.split(' is a ', 1)[1].split('.')[0].strip()
            elif ' is an ' in s.lower():
                d = 'is an ' + s.split(' is an ', 1)[1].split('.')[0].strip()
            else:
                continue
            if len(d) > 60:
                d = d[:57] + "..."
            other_defs.append(d)
    
    if len(other_defs) >= 3:
        distractors = random.sample(other_defs, 3)
    else:
        distractors = [
            "is a programming language",
            "is a software framework",
            "is a database system",
            "is an operating system",
            "is a hardware component",
            "is a network protocol"
        ][:3]
    
    # Shuffle options
    options = [correct_answer] + distractors
    random.shuffle(options)
    
    return {
        'id': index,
        'question': question,
        'options': options,
        'correct': correct_answer,
        'type': 'MCQ',
        'category': 'Definition'
    }

def generate_mcq_date(sentence, index, all_sentences):
    """Generate MCQ from dated fact"""
    
    # Find date
    date_match = re.search(r'\b(19|20)\d{2}\b', sentence)
    if not date_match:
        return None
    
    date = date_match.group(0)
    
    # Extract subject (first capitalized word)
    words = sentence.split()
    subject = None
    for word in words[:5]:
        if word[0].isupper() and len(word) > 2:
            subject = word
            break
    
    if not subject:
        subject = words[0] if words else "This"
    
    # Create question
    if ' was ' in sentence.lower() or ' were ' in sentence.lower():
        question = f"In what year was {subject} developed/created/introduced?"
    else:
        question = f"What year is mentioned in relation to {subject}?"
    
    correct_answer = date
    
    # Generate wrong years
    wrong_years = []
    all_years = [1990, 1995, 1998, 2000, 2005, 2008, 2010, 2012, 2015, 2018, 2020]
    current_year = int(date)
    
    for year in all_years:
        if year != current_year and len(wrong_years) < 3:
            wrong_years.append(str(year))
    
    while len(wrong_years) < 3:
        wrong_years.append(str(current_year + random.randint(1, 5)))
    
    options = [correct_answer] + wrong_years[:3]
    random.shuffle(options)
    
    return {
        'id': index,
        'question': question,
        'options': options,
        'correct': correct_answer,
        'type': 'MCQ',
        'category': 'Historical Fact'
    }

def generate_mcq_composition(sentence, index, all_sentences):
    """Generate MCQ about composition"""
    
    # Extract subject and components
    subject = None
    components = None
    
    words = sentence.split()
    for word in words[:5]:
        if word[0].isupper() and len(word) > 2:
            subject = word
            break
    
    if not subject:
        subject = words[0] if words else "This"
    
    if ' contains ' in sentence.lower():
        components = sentence.lower().split(' contains ', 1)[1].split('.')[0]
    elif ' consists of ' in sentence.lower():
        components = sentence.lower().split(' consists of ', 1)[1].split('.')[0]
    elif ' comprises ' in sentence.lower():
        components = sentence.lower().split(' comprises ', 1)[1].split('.')[0]
    elif ' includes ' in sentence.lower():
        components = sentence.lower().split(' includes ', 1)[1].split('.')[0]
    
    if not components:
        return None
    
    components = components.strip()
    if len(components) > 60:
        components = components[:57] + "..."
    
    # Create question
    question = f"What does {subject} consist of or contain?"
    correct_answer = components.capitalize()
    
    # Generate wrong answers
    distractors = [
        "Data and information",
        "Hardware and software",
        "Multiple components",
        "Various elements",
        "Different modules",
        "Several parts"
    ]
    
    random.shuffle(distractors)
    
    options = [correct_answer] + distractors[:3]
    random.shuffle(options)
    
    return {
        'id': index,
        'question': question,
        'options': options,
        'correct': correct_answer,
        'type': 'MCQ',
        'category': 'Composition'
    }

def generate_mcq_function(sentence, index, all_sentences):
    """Generate MCQ about function/purpose"""
    
    # Extract subject
    words = sentence.split()
    subject = None
    
    for word in words[:5]:
        if word[0].isupper() and len(word) > 2:
            subject = word
            break
    
    if not subject:
        subject = words[0] if words else "This"
    
    # Extract function
    function = None
    
    if ' is used ' in sentence.lower():
        function = sentence.lower().split(' is used ', 1)[1].split('.')[0]
    elif ' are used ' in sentence.lower():
        function = sentence.lower().split(' are used ', 1)[1].split('.')[0]
    elif ' enables ' in sentence.lower():
        function = sentence.lower().split(' enables ', 1)[1].split('.')[0]
    elif ' allows ' in sentence.lower():
        function = sentence.lower().split(' allows ', 1)[1].split('.')[0]
    elif ' provides ' in sentence.lower():
        function = sentence.lower().split(' provides ', 1)[1].split('.')[0]
    
    if not function:
        return None
    
    function = function.strip()
    if len(function) > 60:
        function = function[:57] + "..."
    
    # Create question
    question = f"What is the purpose or function of {subject}?"
    correct_answer = function.capitalize()
    
    # Generate wrong answers
    distractors = [
        "To store and manage data",
        "To process user input",
        "To display information",
        "To connect to networks",
        "To analyze statistics",
        "To generate reports"
    ]
    
    random.shuffle(distractors)
    
    options = [correct_answer] + distractors[:3]
    random.shuffle(options)
    
    return {
        'id': index,
        'question': question,
        'options': options,
        'correct': correct_answer,
        'type': 'MCQ',
        'category': 'Function'
    }

def generate_mcq_fact(sentence, index, all_sentences):
    """Generate MCQ from general fact"""
    
    # Extract subject
    words = sentence.split()
    subject = None
    
    for word in words[:5]:
        if word[0].isupper() and len(word) > 2:
            subject = word
            break
    
    if not subject:
        subject = words[0] if words else "the topic"
    
    # Create question
    question = f"According to the document, which statement about {subject} is correct?"
    
    # Correct answer (the sentence itself)
    correct_answer = sentence
    if len(correct_answer) > 100:
        correct_answer = correct_answer[:97] + "..."
    
    # Generate wrong answers
    distractors = []
    
    # Take other sentences as wrong answers
    other_sentences = random.sample([s for s in all_sentences if s != sentence], min(3, len(all_sentences)-1))
    
    for s in other_sentences:
        distractor = s
        if len(distractor) > 100:
            distractor = distractor[:97] + "..."
        distractors.append(distractor)
    
    while len(distractors) < 3:
        distractors.append(f"This information about {subject} is not mentioned in the document")
    
    options = [correct_answer] + distractors[:3]
    random.shuffle(options)
    
    return {
        'id': index,
        'question': question,
        'options': options,
        'correct': correct_answer,
        'type': 'MCQ',
        'category': 'General Fact'
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract text
        text = extract_text_from_pdf(filepath)
        
        if not text.strip():
            return render_template('index.html', error="Could not extract text from PDF. Make sure it's not a scanned image.")
        
        # Get number of questions
        num_questions = int(request.form.get('num_questions', 5))
        
        # Extract sentences
        all_sentences = extract_sentences(text)
        
        if len(all_sentences) < 3:
            return render_template('index.html', error="Not enough text content in PDF to generate questions.")
        
        # Categorize sentences
        definitions = extract_definitions(all_sentences)
        dated_facts = extract_facts_with_dates(all_sentences)
        composition_facts = extract_composition_facts(all_sentences)
        function_facts = extract_function_facts(all_sentences)
        
        # Generate MCQs
        quiz_data = []
        used_subjects = set()
        
        # 1. Generate from definitions (best questions)
        for sentence in definitions:
            if len(quiz_data) >= num_questions:
                break
            
            question = generate_mcq_definition(sentence, len(quiz_data), all_sentences)
            if question:
                # Extract subject from question
                subject = question['question'].replace('What is ', '').replace('?', '').strip()
                if subject not in used_subjects:
                    quiz_data.append(question)
                    used_subjects.add(subject)
        
        # 2. Generate from dated facts
        for sentence in dated_facts:
            if len(quiz_data) >= num_questions:
                break
            
            question = generate_mcq_date(sentence, len(quiz_data), all_sentences)
            if question:
                subject = question['question'].split(' was ')[0].replace('In what year was ', '').strip()
                if subject not in used_subjects:
                    quiz_data.append(question)
                    used_subjects.add(subject)
        
        # 3. Generate from composition facts
        for sentence in composition_facts:
            if len(quiz_data) >= num_questions:
                break
            
            question = generate_mcq_composition(sentence, len(quiz_data), all_sentences)
            if question:
                subject = question['question'].replace('What does ', '').replace(' consist of or contain?', '').strip()
                if subject not in used_subjects:
                    quiz_data.append(question)
                    used_subjects.add(subject)
        
        # 4. Generate from function facts
        for sentence in function_facts:
            if len(quiz_data) >= num_questions:
                break
            
            question = generate_mcq_function(sentence, len(quiz_data), all_sentences)
            if question:
                subject = question['question'].replace('What is the purpose or function of ', '').replace('?', '').strip()
                if subject not in used_subjects:
                    quiz_data.append(question)
                    used_subjects.add(subject)
        
        # 5. Generate from general facts if still need more
        if len(quiz_data) < num_questions:
            remaining = [s for s in all_sentences if s not in definitions and 
                        s not in dated_facts and 
                        s not in composition_facts and 
                        s not in function_facts]
            
            for sentence in remaining:
                if len(quiz_data) >= num_questions:
                    break
                
                question = generate_mcq_fact(sentence, len(quiz_data), all_sentences)
                if question:
                    quiz_data.append(question)
        
        # Ensure we have exactly num_questions
        quiz_data = quiz_data[:num_questions]
        
        if not quiz_data:
            return render_template('index.html', error="Could not generate MCQs from this PDF. Try another file.")
        
        # Save to session
        session['quiz'] = quiz_data
        session['total_questions'] = len(quiz_data)
        
        return redirect(url_for('quiz'))
    
    return redirect(url_for('index'))

@app.route('/quiz')
def quiz():
    quiz_data = session.get('quiz', [])
    if not quiz_data:
        return redirect(url_for('index'))
    return render_template('quiz.html', quiz=quiz_data)

@app.route('/submit-quiz', methods=['POST'])
def submit_quiz():
    quiz_data = session.get('quiz', [])
    if not quiz_data:
        return redirect(url_for('index'))
    
    # Get user answers
    user_answers = {}
    for key, value in request.form.items():
        if key.startswith('q_'):
            q_id = int(key[2:])
            user_answers[q_id] = value
    
    # Calculate score
    score = 0
    results = []
    
    for q in quiz_data:
        q_id = q['id']
        user_answer = user_answers.get(q_id, 'Not answered')
        correct_answer = q['correct']
        
        is_correct = (user_answer == correct_answer)
        
        if is_correct:
            score += 1
        
        results.append({
            'question': q['question'],
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct,
            'category': q.get('category', 'General')
        })
    
    percentage = (score / len(quiz_data)) * 100
    
    return render_template('result.html', 
                          score=score, 
                          total=len(quiz_data), 
                          percentage=round(percentage, 1),
                          results=results)

@app.route('/reset')
def reset():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
