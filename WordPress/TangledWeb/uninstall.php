<?php

if (!defined('WP_UNINSTALL_PLUGIN')) {
    die;
}

require_once( ABSPATH . 'wp-admin/includes/upgrade.php' );

global $wpdb;
$wpdb->query("DROP TABLE IF EXISTS {$wpdb->prefix}tangled_web_redir");
$wpdb->query("DROP TABLE IF EXISTS {$wpdb->prefix}tangled_web_index");
$wpdb->query("DROP TABLE IF EXISTS {$wpdb->prefix}tangled_web_data");

?>