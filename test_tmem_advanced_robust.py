"""
Evaluate T-MEM on LoCoMo using the same robust A-MEM benchmark pipeline.

This mirrors ``test_advanced_robust.py`` and keeps the following unchanged:
  - note construction prompts
  - memory evolution / linking prompts
  - query keyword generation
  - answer generation prompts
  - QA metrics and category aggregation

The only benchmark-time difference is retrieval ranking:
  A-MEM -> cosine only
  T-MEM -> alpha * cosine + (1 - alpha) * temporal relevance
"""

from memory_layer_robust import RobustLLMController
from memory_layer_tmem_robust import (
    TemporalAwareRobustAgenticMemorySystem,
    TemporalRetrievalConfig,
)
from llm_text_parsers import (
    parse_plain_text_answer,
    parse_relevant_parts,
    parse_keywords_response,
)
import os
import json
import argparse
import logging
from typing import Optional
from datetime import datetime
from collections import defaultdict
import pickle
import random
import time

import nltk

from load_dataset import load_locomo_dataset
from utils import calculate_metrics, aggregate_metrics


# Download required NLTK data
try:
    nltk.data.find("tokenizers/punkt")
    nltk.data.find("wordnet")
except LookupError:
    nltk.download("punkt")
    nltk.download("wordnet")

logger = logging.getLogger("tmem_robust_eval")


class TMemAdvancedMemAgent:
    """Agent that reuses the robust A-MEM pipeline with temporal-aware retrieval."""

    def __init__(
        self,
        model: str,
        backend: str,
        retrieve_k: int,
        temperature_c5: float,
        temporal_config: TemporalRetrievalConfig,
        sglang_host: str = "http://localhost",
        sglang_port: int = 30000,
    ):
        self.memory_system = TemporalAwareRobustAgenticMemorySystem(
            model_name="all-MiniLM-L6-v2",
            llm_backend=backend,
            llm_model=model,
            sglang_host=sglang_host,
            sglang_port=sglang_port,
            temporal_config=temporal_config,
        )
        self.retriever_llm = RobustLLMController(
            backend=backend,
            model=model,
            api_key=None,
            sglang_host=sglang_host,
            sglang_port=sglang_port,
        )
        self.retrieve_k = retrieve_k
        self.temperature_c5 = temperature_c5

    def add_memory(self, content: str, time: Optional[str] = None):
        self.memory_system.add_note(content, time=time)

    def retrieve_memory(
        self,
        content: str,
        k: int = 10,
        question_category: Optional[int] = None,
    ):
        return self.memory_system.find_related_memories_raw(
            content,
            k=k,
            question_category=question_category,
        )

    def retrieve_memory_llm(self, memories_text: str, query: str):
        """Select relevant parts of conversation memories — plain text, no JSON schema."""
        prompt = f"""Given the following conversation memories and a question, select the most relevant parts of the conversation that would help answer the question. Include the date/time if available.

Conversation memories:
{memories_text}

Question: {query}

Return only the relevant parts of the conversation that would help answer this specific question.
If no parts are relevant, return the input unchanged."""

        response = self.retriever_llm.llm.get_completion(prompt)
        return parse_relevant_parts(response)

    def generate_query_llm(self, question: str):
        """Generate query keywords — plain text, no JSON schema."""
        prompt = f"""Given the following question, generate several keywords separated by commas.

Question: {question}

Keywords:"""

        response = self.retriever_llm.llm.get_completion(prompt)
        result = parse_keywords_response(response)
        logger.debug("generate_query_llm response: %s", result)
        return result

    def answer_question(self, question: str, category: int, answer: str) -> tuple:
        """Generate an answer using the same prompting strategy as robust A-MEM."""
        keywords = self.generate_query_llm(question)
        raw_context = self.retrieve_memory(
            keywords,
            k=self.retrieve_k,
            question_category=category,
        )
        context = raw_context

        assert category in [1, 2, 3, 4, 5]

        if category == 5:
            answer_tmp = []
            if random.random() < 0.5:
                answer_tmp.append("Not mentioned in the conversation")
                answer_tmp.append(answer)
            else:
                answer_tmp.append(answer)
                answer_tmp.append("Not mentioned in the conversation")
            user_prompt = f"""Based on the context: {context}, answer the following question. {question}

Select the correct answer: {answer_tmp[0]} or {answer_tmp[1]}  Short answer:"""
            temperature = self.temperature_c5
        elif category == 2:
            user_prompt = f"""Based on the context: {context}, answer the following question. Use DATE of CONVERSATION to answer with an approximate date.
Please generate the shortest possible answer, using words from the conversation where possible, and avoid using any subjects.

Question: {question} Short answer:"""
            temperature = 0.7
        elif category == 3:
            user_prompt = f"""Based on the context: {context}, write an answer in the form of a short phrase for the following question. Answer with exact words from the context whenever possible.

Question: {question} Short answer:"""
            temperature = 0.7
        else:
            user_prompt = f"""Based on the context: {context}, write an answer in the form of a short phrase for the following question. Answer with exact words from the context whenever possible.

Question: {question} Short answer:"""
            temperature = 0.7

        try:
            response = self.memory_system.llm_controller.llm.get_completion(
                user_prompt, temperature=temperature,
            )
        except Exception as e:
            logger.warning("answer_question failed: %s — returning empty", e)
            response = ""
        return response, user_prompt, raw_context


def setup_logger(log_file: Optional[str] = None) -> logging.Logger:
    """Set up logging configuration."""
    eval_logger = logging.getLogger("locomo_eval_tmem_robust")
    eval_logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    eval_logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        eval_logger.addHandler(file_handler)

    return eval_logger


def _sample_turn_count(sample) -> int:
    """Count total conversation turns in one LoCoMo sample."""
    return sum(len(session.turns) for session in sample.conversation.sessions.values())


def evaluate_dataset(
    dataset_path: str,
    model: str,
    output_path: Optional[str] = None,
    ratio: float = 1.0,
    backend: str = "openai",
    temperature_c5: float = 0.5,
    retrieve_k: int = 10,
    sglang_host: str = "http://localhost",
    sglang_port: int = 30000,
    temporal_config: Optional[TemporalRetrievalConfig] = None,
):
    """Evaluate T-MEM on the LoCoMo dataset using the robust A-MEM pipeline."""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    log_filename = f"eval_tmem_robust_{model}_{backend}_ratio{ratio}_{timestamp}.log"
    log_path = os.path.join(os.path.dirname(__file__), "logs", log_filename)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    eval_logger = setup_logger(log_path)
    eval_logger.info("Loading dataset from %s", dataset_path)
    eval_logger.info("Using T-MEM robust memory layer (A-MEM pipeline + temporal retrieval)")

    samples = load_locomo_dataset(dataset_path)
    eval_logger.info("Loaded %d samples", len(samples))

    if ratio < 1.0:
        num_samples = max(1, int(len(samples) * ratio))
        samples = samples[:num_samples]
        eval_logger.info("Using %d samples (%.1f%% of dataset)", num_samples, ratio * 100.0)

    results = []
    all_metrics = []
    all_categories = []
    total_questions = 0
    category_counts = defaultdict(int)
    error_num = 0

    # Reuse the same cache namespace as robust A-MEM so the memory bank itself is identical.
    memories_dir = os.path.join(
        os.path.dirname(__file__),
        "cached_memories_robust_{}_{}".format(backend, model),
    )
    os.makedirs(memories_dir, exist_ok=True)
    allow_categories = [1, 2, 3, 4, 5]
    temporal_config = temporal_config or TemporalRetrievalConfig()

    for sample_idx, sample in enumerate(samples):
        agent = TMemAdvancedMemAgent(
            model,
            backend,
            retrieve_k,
            temperature_c5,
            temporal_config,
            sglang_host,
            sglang_port,
        )

        memory_cache_file = os.path.join(memories_dir, f"memory_cache_sample_{sample_idx}.pkl")
        retriever_cache_file = os.path.join(memories_dir, f"retriever_cache_sample_{sample_idx}.pkl")
        retriever_cache_embeddings_file = os.path.join(
            memories_dir, f"retriever_cache_embeddings_sample_{sample_idx}.npy"
        )

        if os.path.exists(memory_cache_file):
            eval_logger.info("Loading cached memories for sample %d", sample_idx)
            with open(memory_cache_file, "rb") as f:
                cached_memories = pickle.load(f)
            agent.memory_system.memories = cached_memories
            if os.path.exists(retriever_cache_file):
                eval_logger.info("Found retriever cache files")
                agent.memory_system.retriever = agent.memory_system.retriever.load(
                    retriever_cache_file, retriever_cache_embeddings_file
                )
            else:
                eval_logger.info("No retriever cache found, loading from memory")
                agent.memory_system.retriever = agent.memory_system.retriever.load_from_local_memory(
                    cached_memories, "all-MiniLM-L6-v2"
                )
            eval_logger.info("Successfully loaded %d memories", len(cached_memories))
        else:
            eval_logger.info("No cached memories found for sample %d. Creating new memories.", sample_idx)
            session_items = list(sample.conversation.sessions.items())
            total_sessions = len(session_items)
            total_turns = _sample_turn_count(sample)
            built_count = 0
            build_started_at = time.perf_counter()
            progress_every = 10

            eval_logger.info(
                "Building memory cache for sample %d: %d sessions, %d turns",
                sample_idx,
                total_sessions,
                total_turns,
            )

            for session_pos, (_, turns) in enumerate(session_items, start=1):
                for turn in turns.turns:
                    turn_datetime = turns.date_time
                    conversation_tmp = "Speaker " + turn.speaker + "says : " + turn.text
                    agent.add_memory(conversation_tmp, time=turn_datetime)
                    built_count += 1

                    if built_count % progress_every == 0 or built_count == total_turns:
                        elapsed = time.perf_counter() - build_started_at
                        eval_logger.info(
                            "Sample %d memory build progress: %d/%d turns (%.1f%%) in %.1fs",
                            sample_idx,
                            built_count,
                            total_turns,
                            (built_count / total_turns * 100.0) if total_turns else 100.0,
                            elapsed,
                        )

                elapsed = time.perf_counter() - build_started_at
                eval_logger.info(
                    "Completed session %d/%d for sample %d (%d/%d turns, %.1fs elapsed)",
                    session_pos,
                    total_sessions,
                    sample_idx,
                    built_count,
                    total_turns,
                    elapsed,
                )

            memories_to_cache = agent.memory_system.memories
            with open(memory_cache_file, "wb") as f:
                pickle.dump(memories_to_cache, f)
            agent.memory_system.retriever.save(retriever_cache_file, retriever_cache_embeddings_file)
            eval_logger.info("Successfully cached %d memories", len(memories_to_cache))

        eval_logger.info("Processing sample %d/%d", sample_idx + 1, len(samples))

        for qa in sample.qa:
            if int(qa.category) in allow_categories:
                total_questions += 1
                category_counts[qa.category] += 1

                prediction, user_prompt, raw_context = agent.answer_question(
                    qa.question, qa.category, qa.final_answer
                )
                prediction = parse_plain_text_answer(prediction)

                eval_logger.info("Question %d: %s", total_questions, qa.question)
                eval_logger.info("Prediction: %s", prediction)
                eval_logger.info("Reference: %s", qa.final_answer)
                eval_logger.info("User Prompt: %s", user_prompt)
                eval_logger.info("Category: %s", qa.category)
                eval_logger.info("Raw Context: %s", raw_context)

                metrics = calculate_metrics(prediction, qa.final_answer) if qa.final_answer else {
                    "exact_match": 0, "f1": 0.0, "rouge1_f": 0.0, "rouge2_f": 0.0,
                    "rougeL_f": 0.0, "bleu1": 0.0, "bleu2": 0.0, "bleu3": 0.0,
                    "bleu4": 0.0, "bert_f1": 0.0, "meteor": 0.0, "sbert_similarity": 0.0,
                }

                all_metrics.append(metrics)
                all_categories.append(qa.category)
                results.append(
                    {
                        "sample_id": sample_idx,
                        "question": qa.question,
                        "prediction": prediction,
                        "reference": qa.final_answer,
                        "category": qa.category,
                        "metrics": metrics,
                    }
                )

                if total_questions % 10 == 0:
                    eval_logger.info("Processed %d questions", total_questions)

    aggregate_results = aggregate_metrics(all_metrics, all_categories)
    final_results = {
        "model": model,
        "dataset": dataset_path,
        "memory_layer": "tmem_robust",
        "temporal_config": {
            "decay_lambda": temporal_config.decay_lambda,
            "blend_alpha": temporal_config.blend_alpha,
            "decay_age_unit": temporal_config.decay_age_unit,
            "use_decay_only_temporal": temporal_config.use_decay_only_temporal,
            "reinforce_beta": temporal_config.reinforce_beta,
            "link_gamma": temporal_config.link_gamma,
            "update_access_stats": temporal_config.update_access_stats,
            "candidate_pool_size": temporal_config.candidate_pool_size,
            "semantic_anchor_count": temporal_config.semantic_anchor_count,
            "semantic_margin_to_skip_temporal": temporal_config.semantic_margin_to_skip_temporal,
            "temporal_score_floor": temporal_config.temporal_score_floor,
            "temporal_categories": list(temporal_config.temporal_categories),
        },
        "total_questions": total_questions,
        "category_distribution": {
            str(cat): count for cat, count in category_counts.items()
        },
        "aggregate_metrics": aggregate_results,
        "individual_results": results,
    }
    eval_logger.info("Error number: %d", error_num)

    if output_path:
        with open(output_path, "w") as f:
            json.dump(final_results, f, indent=2)
        eval_logger.info("Results saved to %s", output_path)

    eval_logger.info("Evaluation Summary:")
    eval_logger.info("Total questions evaluated: %d", total_questions)
    eval_logger.info("Category Distribution:")
    for category, count in sorted(category_counts.items()):
        eval_logger.info(
            "Category %s: %d questions (%.1f%%)",
            category,
            count,
            count / total_questions * 100.0,
        )

    eval_logger.info("Aggregate Metrics:")
    for split_name, metrics in aggregate_results.items():
        eval_logger.info("%s:", split_name.replace("_", " ").title())
        for metric_name, stats in metrics.items():
            eval_logger.info("  %s:", metric_name)
            for stat_name, value in stats.items():
                eval_logger.info("    %s: %.4f", stat_name, value)

    return final_results


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate T-MEM on LoCoMo using the same robust A-MEM benchmark flow"
    )
    parser.add_argument("--dataset", type=str, default="data/locomo10.json",
                        help="Path to the dataset file")
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                        help="Model to use")
    parser.add_argument("--output", type=str, default=None,
                        help="Path to save evaluation results")
    parser.add_argument("--ratio", type=float, default=1.0,
                        help="Ratio of dataset to evaluate (0.0 to 1.0)")
    parser.add_argument("--backend", type=str, default="openai",
                        help="Backend to use (openai, ollama, sglang, or vllm)")
    parser.add_argument("--temperature_c5", type=float, default=0.5,
                        help="Temperature for category 5 questions")
    parser.add_argument("--retrieve_k", type=int, default=10,
                        help="Number of memories to retrieve")
    parser.add_argument("--sglang_host", type=str, default="http://localhost",
                        help="SGLang server host (for sglang backend)")
    parser.add_argument("--sglang_port", type=int, default=30000,
                        help="SGLang server port (for sglang backend)")

    parser.add_argument("--decay_lambda", type=float, default=0.1,
                        help="Lambda in exp(-lambda * age)")
    parser.add_argument("--blend_alpha", type=float, default=0.9,
                        help="Weight on cosine similarity in the blended T-MEM score")
    parser.add_argument("--decay_age_unit", type=str, default="months_equiv",
                        choices=["months_equiv", "days"],
                        help="Age unit for temporal decay")
    parser.add_argument("--reinforce_beta", type=float, default=0.5,
                        help="Access reinforcement weight (used only in full relevance mode)")
    parser.add_argument("--link_gamma", type=float, default=0.3,
                        help="Link bonus weight (used only in full relevance mode)")
    parser.add_argument("--full_relevance", action="store_true",
                        help="Use decay * reinforce * link_bonus instead of decay-only mode")
    parser.add_argument("--update_access_stats", action="store_true",
                        help="Increment retrieval_count during evaluation for full-relevance experiments")
    parser.add_argument("--candidate_pool_size", type=int, default=20,
                        help="Semantic top-N pool that T-MEM reranks temporally")
    parser.add_argument("--semantic_anchor_count", type=int, default=2,
                        help="Number of top semantic memories to keep fixed before reranking the rest")
    parser.add_argument("--semantic_margin_to_skip_temporal", type=float, default=0.05,
                        help="Skip temporal reranking when the best semantic match leads by this margin")
    parser.add_argument("--temporal_score_floor", type=float, default=0.25,
                        help="Lower bound applied to normalized temporal scores within the candidate pool")
    parser.add_argument("--temporal_categories", type=int, nargs="+", default=[2],
                        help="Question categories where temporal reranking is allowed")

    args = parser.parse_args()

    if args.ratio <= 0.0 or args.ratio > 1.0:
        raise ValueError("Ratio must be between 0.0 and 1.0")

    dataset_path = os.path.join(os.path.dirname(__file__), args.dataset)
    output_path = os.path.join(os.path.dirname(__file__), args.output) if args.output else None
    temporal_config = TemporalRetrievalConfig(
        decay_lambda=args.decay_lambda,
        blend_alpha=args.blend_alpha,
        decay_age_unit=args.decay_age_unit,
        use_decay_only_temporal=not args.full_relevance,
        reinforce_beta=args.reinforce_beta,
        link_gamma=args.link_gamma,
        update_access_stats=args.update_access_stats,
        candidate_pool_size=args.candidate_pool_size,
        semantic_anchor_count=args.semantic_anchor_count,
        semantic_margin_to_skip_temporal=args.semantic_margin_to_skip_temporal,
        temporal_score_floor=args.temporal_score_floor,
        temporal_categories=tuple(args.temporal_categories),
    )

    evaluate_dataset(
        dataset_path,
        args.model,
        output_path,
        args.ratio,
        args.backend,
        args.temperature_c5,
        args.retrieve_k,
        args.sglang_host,
        args.sglang_port,
        temporal_config,
    )


if __name__ == "__main__":
    main()
