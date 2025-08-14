from typing import Dict, List, Optional, Callable
from datetime import datetime
from utilties.search_utilities import remove_think_tags, format_findings_to_text, print_search_results
import os
from utilties.enums import KnowledgeAccumulationApproach
from config import get_llm, get_search, SEARCH_ITERATIONS, QUESTIONS_PER_ITERATION
import config
from citation_handler import CitationHandler
from datetime import datetime
from utilties.search_utilities import extract_links_from_search_results

class AdvancedSearchSystem:
    def __init__(self):
        self.search = get_search()
        self.model = get_llm()
        self.max_iterations = SEARCH_ITERATIONS
        self.questions_per_iteration = QUESTIONS_PER_ITERATION
        self.context_limit = 5000
        self.questions_by_iteration = {}
        self.citation_handler = CitationHandler(self.model)
        self.progress_callback = None

    def set_progress_callback(self, callback: Callable[[str, int, dict], None]) -> None:
        """Set a callback function to receive progress updates.
        
        Args:
            callback: Function that takes (message, progress_percent, metadata)
        """
        self.progress_callback = callback

    def _update_progress(self, message: str, progress_percent: int = None, metadata: dict = None) -> None:
        """Send a progress update via the callback if available.
        
        Args:
            message: Description of the current progress state
            progress_percent: Progress percentage (0-100), if applicable
            metadata: Additional data about the progress state
        """
        if self.progress_callback:
            self.progress_callback(message, progress_percent, metadata or {})

    def _get_follow_up_questions(self, current_knowledge: str, query: str) -> List[str]:
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d")
        
        self._update_progress("Generating follow-up questions...", None, {"iteration": len(self.questions_by_iteration)})
        
        if self.questions_by_iteration:
            prompt = f"""Critically reflect current knowledge (e.g., timeliness), what {self.questions_per_iteration} high-quality internet search questions remain unanswered to exactly answer the query?
            Query: {query}
            Today: {current_time} 
            Past questions: {str(self.questions_by_iteration)}
            Knowledge: {current_knowledge}
            Include questions that critically reflect current knowledge.
            \n\n\nFormat: One question per line, e.g. \n Q: question1 \n Q: question2\n\n"""
        else:
            prompt = f" You will have follow up questions. First, identify if your knowledge is outdated (high chance). Today: {current_time}. Generate {self.questions_per_iteration} high-quality internet search questions to exactly answer: {query}\n\n\nFormat: One question per line, e.g. \n Q: question1 \n Q: question2\n\n"

        response = self.model.invoke(prompt)
        questions = [
            q.replace("Q:", "").strip()
            for q in remove_think_tags(response.content).split("\n")
            if q.strip().startswith("Q:")
        ][: self.questions_per_iteration]
        
        self._update_progress(
            f"Generated {len(questions)} follow-up questions", 
            None, 
            {"questions": questions}
        )
        
        return questions

    def _compress_knowledge(self, current_knowledge: str, query: str) -> List[str]:
        self._update_progress("Compressing and summarizing knowledge...", None)
        
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d")
        if self.questions_by_iteration:
            prompt = f"""First provide a high-quality 1 page explanation based on sources (Date today: {current_time}). Keep citations and source link directly in text position. Never make up sources. Than provide a exact high-quality one sentence-long answer to the query. 

            Knowledge: {current_knowledge}
            Query: {query}
            \n\n\nFormat: text summary\n\n"""
        response = self.model.invoke(prompt)
        
        self._update_progress("Knowledge compression complete", None)
        return remove_think_tags(response.content)

    def analyze_topic(self, query: str) -> Dict:
        findings = []
        current_knowledge = ""
        iteration = 0
        total_iterations = self.max_iterations
        
        self._update_progress("Initializing research system", 5, {
            "phase": "init",
            "iterations_planned": total_iterations
        })

        while iteration < self.max_iterations:
            iteration_progress_base = (iteration / total_iterations) * 100
            self._update_progress(f"Starting iteration {iteration + 1} of {total_iterations}", 
                                 int(iteration_progress_base),
                                 {"phase": "iteration_start", "iteration": iteration + 1})
            
            # Generate questions for this iteration
            questions = self._get_follow_up_questions(current_knowledge, query)
            self.questions_by_iteration[iteration] = questions
            
            question_count = len(questions)
            for q_idx, question in enumerate(questions):
                question_progress_base = iteration_progress_base + (((q_idx+1) / question_count) * (100/total_iterations) * 0.5)
                
                self._update_progress(f"Searching for: {question}", 
                                     int(question_progress_base),
                                     {"phase": "search", "iteration": iteration + 1, "question_index": q_idx + 1})
                
                search_results = self.search.run(question)
                limited_knowledge = (
                    current_knowledge[-self.context_limit :]
                    if len(current_knowledge) > self.context_limit
                    else current_knowledge
                )
                
                self._update_progress(f"Found {len(search_results)} results for question: {question}", 
                                    int(question_progress_base + 2),
                                    {"phase": "search_complete", "result_count": len(search_results)})
                
                print("len search", len(search_results))
                
                if len(search_results) == 0:
                    continue

                print_search_results(search_results) # only links

                self._update_progress(f"Analyzing results for: {question}", 
                                     int(question_progress_base + 5),
                                     {"phase": "analysis"})
                
                result = self.citation_handler.analyze_followup(
                    question, search_results, limited_knowledge
                )
                
                if result is not None:
                    findings.append(
                        {
                            "phase": f"Follow-up {iteration}.{questions.index(question) + 1}",
                            "content": result["content"],
                            "question": question,
                            "search_results": search_results,
                            "documents": result["documents"],
                        }
                    )

                    links = extract_links_from_search_results(search_results)
                    results_with_links = str(result) + "\n" + str(links)
                    if config.KNOWLEDGE_ACCUMULATION != KnowledgeAccumulationApproach.NONE:
                        current_knowledge = current_knowledge + "\n\n\n New: \n" + results_with_links
                    
                    print(current_knowledge)
                    if config.KNOWLEDGE_ACCUMULATION == KnowledgeAccumulationApproach.QUESTION:
                        self._update_progress(f"Compress Knowledge for: {question}", 
                                     int(question_progress_base + 0),
                                     {"phase": "analysis"})
                        current_knowledge = self._compress_knowledge(current_knowledge , query)
                    
                    self._update_progress(f"Analysis complete for question: {question}", 
                                         int(question_progress_base + 10),
                                         {"phase": "analysis_complete"})

            iteration += 1
            
            self._update_progress(f"Compressing knowledge after iteration {iteration}", 
                                 int((iteration / total_iterations) * 100 - 5),
                                 {"phase": "knowledge_compression"})
            if config.KNOWLEDGE_ACCUMULATION == KnowledgeAccumulationApproach.ITERATION:
                current_knowledge = self._compress_knowledge(current_knowledge , query)

            
            self._update_progress(f"Iteration {iteration} complete", 
                                 int((iteration / total_iterations) * 100),
                                 {"phase": "iteration_complete", "iteration": iteration})
            
            formatted_findings = self._save_findings(findings, current_knowledge, query)

        self._update_progress("Research complete", 95, {"phase": "complete"})
        
        return {
            "findings": findings,
            "iterations": iteration,
            "questions": self.questions_by_iteration,
            "formatted_findings": formatted_findings,
        }

    def _save_findings(self, findings: List[Dict], current_knowledge: str, query: str):
        self._update_progress("Saving research findings...", None)
        
        formatted_findings = format_findings_to_text(
            findings, current_knowledge, self.questions_by_iteration
        )
        safe_query = "".join(x for x in query if x.isalnum() or x in [" ", "-", "_"])[
            :50
        ]
        safe_query = safe_query.replace(" ", "_").lower()

        output_dir = "research_outputs"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        filename = os.path.join(output_dir, f"formatted_output_{safe_query}.txt")

        with open(filename, "w", encoding="utf-8") as text_file:
            text_file.write(formatted_findings)
            
        self._update_progress("Research findings saved", None, {"filename": filename})
        return formatted_findings