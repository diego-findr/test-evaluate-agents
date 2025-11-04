"""
Test workflow for evaluating candidates with mock data
"""

import logging

from src.config import get_settings, setup_logging
from src.api.dependencies import get_container
from src.services import save_evaluation_result
from .test_data import create_mock_good_candidate, create_mock_bad_candidate


logger = logging.getLogger(__name__)


async def test_evaluation_workflow():
    """Test the complete evaluation workflow with both good and bad candidates."""
    
    # Setup
    settings = get_settings()
    setup_logging(settings)
    
    logger.info("=" * 80)
    logger.info("TESTING MAS-EVAL WORKFLOW WITH MULTIPLE TEST CASES")
    logger.info("=" * 80)
    
    results = []
    
    try:
        # Initialize dependencies
        container = get_container()
        await container.initialize(settings)
        
        # ============= TEST CASE 1: GOOD CANDIDATE =============
        logger.info("\n" + "=" * 80)
        logger.info("TEST CASE 1: GOOD CANDIDATE (Expected: LIKED)")
        logger.info("=" * 80)
        
        good_request = create_mock_good_candidate()
        
        logger.info(f"\n📋 EVALUATING:")
        logger.info(f"   Position: {good_request.offer.job_title}")
        logger.info(f"   Company: {good_request.offer.company_name}")
        logger.info(f"   Candidate: {good_request.candidate.heading}")
        logger.info(f"   Experience: {good_request.candidate.experience_years} years\n")
        
        # Execute evaluation
        good_result = await container.evaluation_service.evaluate(good_request)
        
        # Display results
        logger.info("=" * 80)
        logger.info("🎯 EVALUATION RESULTS - TEST CASE 1")
        logger.info("=" * 80)
        logger.info(f"\n✅ Decision: {'LIKED ❤️' if good_result.liked else 'REJECTED ❌'}")
        logger.info(f"📊 Compatibility Score: {good_result.compatibility}/100")
        logger.info(f"⚠️  Human Review Required: {'YES' if good_result.qa_required_human_review else 'NO'}")
        logger.info(f"\n📝 Final Reason:\n{good_result.reason}\n")
        logger.info(f"🤖 Agent Evaluations:")
        for i, reason in enumerate(good_result.ai_swipe_reasons, 1):
            logger.info(f"\n{i}. {reason}")
        
        # Save results
        save_evaluation_result(good_request, good_result, "good_candidate")
        results.append(("good_candidate", good_result))
        
        # ============= TEST CASE 2: BAD CANDIDATE =============
        logger.info("\n\n" + "=" * 80)
        logger.info("TEST CASE 2: BAD CANDIDATE (Expected: REJECTED)")
        logger.info("=" * 80)
        
        bad_request = create_mock_bad_candidate()
        
        logger.info(f"\n📋 EVALUATING:")
        logger.info(f"   Position: {bad_request.offer.job_title}")
        logger.info(f"   Company: {bad_request.offer.company_name}")
        logger.info(f"   Candidate: {bad_request.candidate.heading}")
        logger.info(f"   Experience: {bad_request.candidate.experience_years} years\n")
        
        # Execute evaluation
        bad_result = await container.evaluation_service.evaluate(bad_request)
        
        # Display results
        logger.info("=" * 80)
        logger.info("🎯 EVALUATION RESULTS - TEST CASE 2")
        logger.info("=" * 80)
        logger.info(f"\n✅ Decision: {'LIKED ❤️' if bad_result.liked else 'REJECTED ❌'}")
        logger.info(f"📊 Compatibility Score: {bad_result.compatibility}/100")
        logger.info(f"⚠️  Human Review Required: {'YES' if bad_result.qa_required_human_review else 'NO'}")
        logger.info(f"\n📝 Final Reason:\n{bad_result.reason}\n")
        logger.info(f"🤖 Agent Evaluations:")
        for i, reason in enumerate(bad_result.ai_swipe_reasons, 1):
            logger.info(f"\n{i}. {reason}")
        
        # Save results
        save_evaluation_result(bad_request, bad_result, "bad_candidate")
        results.append(("bad_candidate", bad_result))
        
        # ============= SUMMARY =============
        logger.info("\n" + "=" * 80)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"\nTotal Tests: {len(results)}")
        for test_name, result in results:
            status = "✅ LIKED" if result.liked else "❌ REJECTED"
            logger.info(f"  • {test_name}: {status} (Score: {result.compatibility}/100)")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        logger.info("=" * 80 + "\n")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {str(e)}", exc_info=True)
        raise

