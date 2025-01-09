async function loadQuestions() {
    try {
        const response = await fetch('/factle/questions.json');
        const data = await response.json();
        return data.questions;
    } catch (error) {
        console.error('Error loading questions:', error);
        return null;
    }
}

function getTodaysQuestion(questions) {
    const today = new Date();
    const monthDay = `${(today.getMonth() + 1).toString().padStart(2, '0')}-${today.getDate().toString().padStart(2, '0')}`;
    
    const todaysQuestion = questions.find(q => q.date === monthDay);
    
    if (!todaysQuestion) {
        console.error('No question found for today');
        return null;
    }

    // Create a copy of options array and shuffle it
    const shuffledOptions = [...todaysQuestion.options].sort(() => Math.random() - 0.5);

    return {
        question: todaysQuestion.question,
        options: shuffledOptions,
        answers: todaysQuestion.answers,
        source: todaysQuestion.source
    };
}

export { loadQuestions, getTodaysQuestion }; 