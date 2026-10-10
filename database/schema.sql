
/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
DROP TABLE IF EXISTS `alerts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alerts` (
  `alert_id` bigint NOT NULL AUTO_INCREMENT,
  `subscription_id` bigint NOT NULL,
  `alert_type` varchar(50) NOT NULL,
  `scheduled_for` datetime DEFAULT NULL,
  `sent_at` datetime DEFAULT NULL,
  `recipient_email` varchar(255) DEFAULT NULL,
  `status` varchar(30) DEFAULT 'pending',
  `message` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`alert_id`),
  KEY `subscription_id` (`subscription_id`),
  CONSTRAINT `alerts_ibfk_1` FOREIGN KEY (`subscription_id`) REFERENCES `subscriptions` (`subscription_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `anomalies`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `anomalies` (
  `anomaly_id` bigint NOT NULL AUTO_INCREMENT,
  `subscription_id` bigint NOT NULL,
  `anomaly_type` varchar(50) NOT NULL,
  `previous_amount` decimal(10,2) DEFAULT NULL,
  `current_amount` decimal(10,2) DEFAULT NULL,
  `anomaly_score` decimal(6,3) DEFAULT NULL,
  `explanation` text,
  `detected_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`anomaly_id`),
  KEY `subscription_id` (`subscription_id`),
  CONSTRAINT `anomalies_ibfk_1` FOREIGN KEY (`subscription_id`) REFERENCES `subscriptions` (`subscription_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `free_trials`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `free_trials` (
  `trial_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `service_name` varchar(255) NOT NULL,
  `reminder_email` varchar(255) NOT NULL,
  `trial_start_at_utc` datetime NOT NULL,
  `trial_end_at_utc` datetime NOT NULL,
  `cancellation_deadline_at_utc` datetime NOT NULL,
  `user_timezone` varchar(100) NOT NULL DEFAULT 'America/Chicago',
  `renewal_amount` decimal(12,2) NOT NULL,
  `currency` char(3) NOT NULL DEFAULT 'USD',
  `billing_period` varchar(30) NOT NULL,
  `cancellation_url` text,
  `status` enum('active','canceled','continued','expired') NOT NULL DEFAULT 'active',
  `created_at_utc` datetime NOT NULL,
  PRIMARY KEY (`trial_id`),
  KEY `idx_trial_reminders` (`status`,`cancellation_deadline_at_utc`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `predictions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `predictions` (
  `prediction_id` bigint NOT NULL AUTO_INCREMENT,
  `subscription_id` bigint NOT NULL,
  `predicted_charge_date` date NOT NULL,
  `predicted_amount` decimal(10,2) DEFAULT NULL,
  `confidence_score` decimal(5,4) DEFAULT NULL,
  `model_version` varchar(50) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`prediction_id`),
  KEY `subscription_id` (`subscription_id`),
  CONSTRAINT `predictions_ibfk_1` FOREIGN KEY (`subscription_id`) REFERENCES `subscriptions` (`subscription_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `risk_scores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `risk_scores` (
  `risk_id` bigint NOT NULL AUTO_INCREMENT,
  `subscription_id` bigint NOT NULL,
  `risk_score` decimal(5,2) NOT NULL,
  `risk_level` varchar(20) DEFAULT NULL,
  `price_change_score` decimal(5,2) DEFAULT NULL,
  `billing_irregularity_score` decimal(5,2) DEFAULT NULL,
  `prediction_uncertainty_score` decimal(5,2) DEFAULT NULL,
  `calculated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`risk_id`),
  KEY `subscription_id` (`subscription_id`),
  CONSTRAINT `risk_scores_ibfk_1` FOREIGN KEY (`subscription_id`) REFERENCES `subscriptions` (`subscription_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `subscriptions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `subscriptions` (
  `subscription_id` bigint NOT NULL AUTO_INCREMENT,
  `merchant_name` varchar(100) NOT NULL,
  `billing_frequency` varchar(30) DEFAULT NULL,
  `average_amount` decimal(10,2) DEFAULT NULL,
  `first_seen_date` date DEFAULT NULL,
  `last_seen_date` date DEFAULT NULL,
  `next_predicted_charge_date` date DEFAULT NULL,
  `next_predicted_amount` decimal(10,2) DEFAULT NULL,
  `detection_confidence` decimal(5,4) DEFAULT NULL,
  `status` varchar(30) DEFAULT 'active',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`subscription_id`),
  KEY `idx_merchant_name` (`merchant_name`),
  KEY `idx_next_charge` (`next_predicted_charge_date`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `transactions` (
  `transaction_id` char(36) NOT NULL,
  `transaction_date` date NOT NULL,
  `description` text NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  `transaction_type` varchar(20) NOT NULL,
  `merchant_ground_truth` varchar(255) DEFAULT NULL,
  `is_subscription_ground_truth` tinyint NOT NULL,
  `event_type_ground_truth` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`transaction_id`),
  KEY `idx_transaction_date` (`transaction_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `trial_reminder_delivery`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trial_reminder_delivery` (
  `delivery_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `trial_id` bigint unsigned NOT NULL,
  `cancellation_deadline_at_utc` datetime NOT NULL,
  `reminder_type` enum('3_day','1_day') NOT NULL,
  `delivery_status` enum('pending','sending','sent','failed','uncertain') NOT NULL DEFAULT 'pending',
  `attempt_count` int NOT NULL DEFAULT '0',
  `last_error` text,
  `updated_at_utc` datetime NOT NULL,
  PRIMARY KEY (`delivery_id`),
  UNIQUE KEY `uq_trial_delivery` (`trial_id`,`cancellation_deadline_at_utc`,`reminder_type`),
  CONSTRAINT `fk_trial_delivery_trial` FOREIGN KEY (`trial_id`) REFERENCES `free_trials` (`trial_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `trial_reminder_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trial_reminder_log` (
  `reminder_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `trial_id` bigint unsigned NOT NULL,
  `cancellation_deadline_at_utc` datetime NOT NULL,
  `reminder_type` enum('3_day','1_day') NOT NULL,
  `recipient_email` varchar(255) NOT NULL,
  `sent_at_utc` datetime NOT NULL,
  PRIMARY KEY (`reminder_id`),
  UNIQUE KEY `uq_trial_reminder` (`trial_id`,`cancellation_deadline_at_utc`,`reminder_type`),
  CONSTRAINT `fk_reminder_trial` FOREIGN KEY (`trial_id`) REFERENCES `free_trials` (`trial_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
