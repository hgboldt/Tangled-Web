<?php
/*
Plugin Name: Tangled Web
Plugin URI: http://www.boldts.net/
Description: Gramps import and presentation
Author: Hans Boldt
Version: 0.9
Author URI: http://www.boldts.net/
License: GPL3
License URI: https://www.gnu.org/licenses/gpl-3.0.html

This plugin is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This plugin is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Tangled Web. If not, see <http://www.gnu.org/licenses/>.
*/

require_once( ABSPATH . 'wp-admin/includes/upgrade.php' );
define('NUM_SUBDIRS', 20);

class TangledWeb
{
    function __construct()
    {
        add_action('admin_menu', [$this, 'create_settings_page']);
        add_action('wp_ajax_tangled_web_search', [$this, 'tangled_web_search']);
        add_action('wp_ajax_nopriv_tangled_web_search', [$this, 'tangled_web_search']);
        add_action('wp_ajax_tangled_web_home', [$this, 'tangled_web_home']);
        add_action('wp_ajax_nopriv_tangled_web_home', [$this, 'tangled_web_home']);

        add_action('rest_api_init', [$this, 'rest_api_init']);

        add_filter('plugin_action_links_' . plugin_basename(__FILE__),
                   [$this, 'settings_page']);

        wp_register_script('tangled-web-js', plugin_dir_url(__FILE__) . 'tangled-web.1.comp.js',
                           ['jquery']);
        wp_enqueue_style('tangled-web-css', plugin_dir_url(__FILE__) . 'tangled-web.1.css');
        add_shortcode('tangled-web', [$this, 'show_html']);
    }

    function rest_api_init()
    {
        register_rest_route
            ('tangled_web', '/start',
             ['methods' => 'POST',
              'callback' => [$this, 'tangled_web_start'],
              'args' =>
                    ['id' =>
                        ['required' => true],
                     'pw' =>
                        ['required' => true],
                    ],
              'permission_callback' => '__return_true',
             ]);

        register_rest_route
            ('tangled_web', '/status',
             ['methods' => 'POST',
              'callback' => [$this, 'tangled_web_status'],
              'args' =>
                    ['tab' =>
                        ['required' => true,
                         'validate_callback' =>
                            function($param, $request, $key) {
                                return $this->check_id_field($param);
                            }
                        ],
                    ],
              'permission_callback' =>
                    function() {
                        return current_user_can('editor');
                    },
              ]);

    }


    function settings_page($links)
    {
        $links[] = '<a href="'
                 . admin_url('options-general.php?page=tw_settings')
                 . '">Settings</a>';
        return $links;
    }

    //----------------//
    //                //
    // Settings page  //
    //                //
    //----------------//

    function create_settings_page()
    {
        add_options_page(
            'Tangled Web Settings',
            'Tangled Web Settings',
            'manage_options',
            'tw_settings',
            [$this, 'settings_page_content'],
            100
        );
    }

    function settings_page_content()
    {
        global $wpdb;

        if (isset($_POST['table-submit']))
        {
            if (!isset($_POST['gonk']) || !wp_verify_nonce($_POST['gonk'], 'tw_update')){
                echo '<div class="error">Sorry, your nonce was not correct. Please try again.</div>';
                exit;
            }

            $command = $_POST['table-submit'];
            if ($command == 'Add table') {
                $this->add_table();
            }
            else {
                $dir = $_POST['dir'];
                if ($this->check_dir_field($dir)) {
                    if ($command == 'Load person index') {
                        $this->load_data($dir);
                    }
                    else if ($command == 'Clear person index') {
                        $this->clear_data($dir);
                    }
                    else if ($command == 'Clear redirect index') {
                        $this->clear_redir_data($dir);
                    }
                    else if ($command == 'Drop') {
                        $this->drop_table($dir);
                    }
                    else if ($command == 'Resume loading') {
                        $this->load_data($dir, true);
                    }
                    else if ($command == 'Load redirect index') {
                        $this->load_redir_data($dir, true);
                    }
                }
            }
        }

        echo '<h2>Tangled Web Settings</h2>';

        // Report on directories
        $sql = "SELECT * FROM {$wpdb->prefix}tangled_web_data;";
        $tables = $wpdb->get_results($sql, ARRAY_A);

        $nonce = wp_nonce_field('tw_update', 'gonk');
        echo <<<SETTINGS3
<style>
table#dirtable {
    border-collapse: collapse;
    border: 1px solid black;
    background-color: #ddf;
}
table#dirtable tr {
    border: none;
}
table#dirtable td, table#dirtable th {
    border: 1px solid black;
    margin: 10px;
    text-align: left;
}
.tw-action-button {
    display: inline-block;
    margin: 1px;
}
.tw-butt {
    border: 1px solid black;
    border-radius: 10px;
    background-image: linear-gradient(#def, #bcf);
}
.tw-butt:hover {
    background-image: linear-gradient(#bcf, #def);
}
.tw-msg {
    border: 2px solid black;
    border-radius: 15px;
    margin: 10px;
    padding: 10px;
    font-weight: bold;
    font-size: 150%;
}
.tw-error {
    background-color: #f89;
}
.tw-status {
    background-color: #8f9;
}
</style>

<h3>Indexes</h3>
<form method="POST" id="add-table-form">$nonce</form>
<table id="dirtable"><tr><th>Instance Id</th><th>Directory</th>
<th>Person index</th><th>Redirect index</th><th>Actions</th></tr>
SETTINGS3;

        if (count($tables) == 0) {
            echo '<tr><td colspan="5">No tables defined. Add a table to continue.</td><tr>';
        }

        foreach ($tables as $dir) {
            $tab = $dir['tabname'];
            $buttons = '';
            if ($dir['status'] == 'table added' || $dir['status'] == 'table empty') {
                $buttons = $this->gen_one_table_form($tab, 'Load person index', $nonce);
            }
            else if ($dir['status'] == 'loading data') {
                $buttons = $this->gen_one_table_form($tab, 'Resume loading', $nonce)
                         . $this->gen_one_table_form($tab, 'Load person index', $nonce)
                         . $this->gen_one_table_form($tab, 'Clear person index', $nonce, true);
            }
            else if ($dir['status'] == 'load complete') {
                $buttons = $this->gen_one_table_form($tab, 'Clear person index', $nonce, true);
            }

            if ($dir['redir_status'] == 'not loaded') {
                $buttons .= $this->gen_one_table_form($tab, 'Load redirect index', $nonce);
            }
            else if ($dir['redir_status'] == 'load complete') {
                $buttons .= $this->gen_one_table_form($tab, 'Clear redirect index', $nonce, true);
            }

            $buttons .= $this->gen_one_table_form($tab, 'Drop', $nonce, true);

            echo "<tr><td>$tab</td><td>{$dir['datadir']}</td>";
            echo "<td><b>{$dir['status']}</b></td>";
            echo "<td><b>{$dir['redir_status']}</b></td>";
            echo "<td>$buttons</td></tr>";
        }

        $table = (isset($_POST['tw-table-name'])) ? $_POST['tw-table-name'] : '';
        $datadir = (isset($_POST['tw-table-datadir'])) ? $_POST['tw-table-datadir'] : '';
        echo '<tr><td><input type="text" name="tw-table-name" id="tw-table-name" form="add-table-form" '
           .                'size="10" value="' . $table . '" /></td>'
           . '<td><input type="text" name="tw-table-datadir" id="tw-table-datadir" form="add-table-form" '
           .                'size="20" value="'. $datadir . '" /></td><td></td><td></td>'
           . '<td><input form="add-table-form" type="submit" name="table-submit" id="table-create" class="tw-butt" value="Add table" /></td></tr>';

        echo '</table>';
    }

    private $form_count = 0;
    private function gen_one_table_form($dir, $type, $nonce, $prompt=false)
    {
        $this->form_count += 1;

        $promptstr = '';
        if ($prompt) {
            $promptstr = 'onclick="return confirm(\'' . $type . ': Are you sure?\')"';
        }

        return <<<ONE_TABLE_FORM
            <form id="tw-table-settings{$this->form_count}" class="tw-action-button" method="POST" >
                 $nonce
                 <input type="hidden" name="dir" value="$dir" />
                 <input type="submit" name="table-submit" id="table-submit{$this->form_count}"
                        class="tw-butt" value="$type" $promptstr />
            </form>
ONE_TABLE_FORM;
    }

    private function add_table()
    {
        global $wpdb;

        // Check table name
        if (!isset($_POST['tw-table-name']) || !$_POST['tw-table-name']) {
            $this->error("Missing table name.");
            return;
        }
        $table = $_POST['tw-table-name'];
        if (!$this->check_id_field($table)) {
            $this->error("Table name $table is not valid.");
            return;
        }

        $sql = $wpdb->prepare("SELECT * FROM {$wpdb->prefix}tangled_web_data
                               WHERE tabname=%s", $table);
        $res = $wpdb->get_results($sql, ARRAY_A);

        if (count($res) > 0) {
            $this->error("Table name $table already exists.");
            return;
        }

        // Check directory name
        if (!isset($_POST['tw-table-datadir']) || !$_POST['tw-table-datadir']) {
            $this->error("Missing directory name.");
            return;
        }
        $datadir = $_POST['tw-table-datadir'];
        if (!$this->check_dir_field($datadir)) {
            $this->error("Directory name $datadir is not valid.");
            return;
        }
        if (!is_dir(ABSPATH . $datadir)) {
            $this->error("Directory $datadir does not exist.");
            return;
        }

        // Do we have a redirect file?
        $redir_status = 'no redirection';
        $redir_fname = ABSPATH . $datadir . '/redir-index';
        if (file_exists($redir_fname)) {
            $redir_status = 'not loaded';
        }

        $date = new DateTime();
        $sql = $wpdb->prepare("INSERT INTO {$wpdb->prefix}tangled_web_data
                               VALUES (%s,%s,%s,%s,%s)",
                               $table, $datadir, 'table added', $redir_status,
                               $date->getTimestamp());
        $res = $wpdb->query($sql);
        $this->status("Table $table added.");

        $this->load_data($table);
        if ($redir_status == 'not loaded') {
            $this->load_redir_data($table);
        }

    }

    private function error($msg)
    {
        echo '<div class="tw-msg tw-error">' . $msg . '</div>';
    }

    private function status($msg)
    {
        echo '<div class="tw-msg tw-status">' . $msg . '</div>';
    }

    private function drop_table($tab) {
        global $wpdb;

        $sql = $wpdb->prepare("DELETE FROM {$wpdb->prefix}tangled_web_data
                               WHERE tabname=%s", $tab);
        $res = $wpdb->query($sql);
        $this->status("Table $tab dropped.");
    }

    private function clear_data($tab)
    {
        global $wpdb;
        $sql = $wpdb->prepare("DELETE FROM {$wpdb->prefix}tangled_web_index WHERE tabname=%s;", $tab);
        $wpdb->query($sql);
        $this->update_status($tab, 'table empty');
        $this->status("Index for $tab cleared.");
    }

    private function clear_redir_data($tab)
    {
        global $wpdb;
        $sql = $wpdb->prepare("DELETE FROM {$wpdb->prefix}tangled_web_redir WHERE tabname=%s;", $tab);
        $wpdb->query($sql);
        $this->update_redir_status($tab, 'not loaded');
        $this->status("Redirection index for $tab cleared.");
    }

    private function load_redir_data($tab)
    {
        global $wpdb;
        $datadir = $this->get_datadir($tab);
        $redir_fname = ABSPATH . $datadir . '/redir-index';
        $fileh = fopen($redir_fname, 'r');
        if (!$fileh)
        {
            return;
        }

        $query = "INSERT INTO {$wpdb->prefix}tangled_web_redir VALUES ";
        $qdata = [];

        $line = fgets($fileh);
        $batch = [];
        $recs_loaded = 0;
        while ($line)
        {
            $recs_loaded += 1;
            $data = explode(',', rtrim($line));
            $batch[] = $wpdb->prepare("(%s,%s,%s)", $data[0], $tab, $data[1]);
            if (count($batch) >= 1000) {
                $wpdb->query($query . implode(',', $batch));
                $batch = [];
            }
            $line = fgets($fileh);
        }

        if ($batch) {
            $wpdb->query($query . implode(',', $batch));
        }

        fclose($fileh);
        $this->update_redir_status($tab, 'load complete');
        $this->status("{$recs_loaded} records loaded to redirection index for  $tab.");
    }


    private function load_data($tab, $continue=false)
    {
        global $wpdb;

        $maxid = 0;
        if ($continue) {
            // How many index items were loaded
            $sql = $wpdb->prepare("SELECT MAX(id) FROM {$wpdb->prefix}tangled_web_index
                                   WHERE tabname=%s", $tab);
            $max_id = $wpdb->get_var($sql);

        }

        $datadir = $this->get_datadir($tab);
        $index_fname = ABSPATH . $datadir . '/search-index.json';

        $fileh = fopen($index_fname, 'r');
        if (!$fileh)
        {
            $this->error("Cannot load file $index_fname.");
        }

        $this->update_status($tab, 'loading data');
        $reccnt = 0;
        $recs_loaded = 0;
        $line = fgets($fileh);
        $batch = [];
        while ($line)
        {
            $reccnt += 1;
            if ($reccnt > $maxid) {
                $rec = json_decode($line, true);
                $rec['id'] = $reccnt;
                $batch[] = $rec;
                if (count($batch) >= 1000) {
                    $this->insert_multiple($tab, $batch);
                    $batch = [];
                }
                $recs_loaded += 1;
            }
            $line = fgets($fileh);
        }

        if ($batch) {
            $this->insert_multiple($tab, $batch);
        }

        fclose($fileh);

        $this->update_status($tab, 'load complete');
        $this->status("{$recs_loaded} records loaded to person index for $tab.");
    }

    private function update_status($tab, $status)
    {
        global $wpdb;
        $sql = $wpdb->prepare("UPDATE {$wpdb->prefix}tangled_web_data
                              SET status=%s WHERE tabname=%s", $status, $tab);
        $res = $wpdb->query($sql);
    }

    private function update_redir_status($tab, $status)
    {
        global $wpdb;
        $sql = $wpdb->prepare("UPDATE {$wpdb->prefix}tangled_web_data
                              SET redir_status=%s WHERE tabname=%s", $status, $tab);
        $res = $wpdb->query($sql);
    }

    private function insert_multiple($tab, $data)
    {
        global $wpdb;
        $query = "INSERT INTO {$wpdb->prefix}tangled_web_index VALUES ";
        $qdata = [];
        foreach ($data as $row) {
            $qdata[] = $wpdb->prepare("(%d,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                      $row['id'], $tab, $row['pid'],
                                      $row['surname'], $row['given'],
                                      $row['gdr'], $row['prim'],
                                      isset($row['bplace']) ? $row['bplace'] : null,
                                      isset($row['btype']) ? $row['btype'] : null,
                                      isset($row['bdate']) ? $row['bdate'] : null,
                                      isset($row['byear']) ? $row['byear'] : null,
                                      isset($row['dplace']) ? $row['dplace'] : null,
                                      isset($row['dtype']) ? $row['dtype'] : null,
                                      isset($row['ddate']) ? $row['ddate'] : null,
                                      isset($row['dyear']) ? $row['dyear'] : null,
                                      $row['csi'], $row['csf'] );
        }
        return $wpdb->query($query . implode(',', $qdata));
    }


    private function check_id_field($name)
    {
        if (preg_match('/[^A-Za-z0-9]/', $name)) {
            return false;
        }
        if (strlen($name) > 10) {
            return false;
        }
        return true;
    }

    private function check_handle($handle)
    {
        if (preg_match('/[^a-f0-9]/', $handle)) {
            return false;
        }
        if (strlen($handle) > 32) {
            return false;
        }
        return true;
    }

    private function check_dir_field($name)
    {
        if (preg_match('/[^A-Za-z0-9. ]/', $name)) {
            return false;
        }
        return true;
    }


    //----------------------//
    //                      //
    // Web site rendering   //
    //                      //
    //----------------------//

    private $what_to_show_full = ['photo', 'note', 'birthdays', 'cloud'];

    function show_html($atts = [], $content = null, $tag = '')
    {
        global $wpdb;

        if (!array_key_exists('id', $atts)) {
            return 'No id specified.';
        }

        $tab = $atts['id'];

        $datadir = $this->get_datadir($tab);
        $globs = $this->get_globals($datadir);

        if (array_key_exists('show', $atts)) {
            $what_to_show = $this->check_show_option($atts['show']);
        }
        else {
            $what_to_show = $this->what_to_show_full;
        }

        $pid = null;
        if (isset($_GET['p'])) {
            $pid = sanitize_text_field($_GET['p']);
        }
        else if (isset($_GET['oldid'])) {
            $oldid = sanitize_text_field($_GET['oldid']);
            if ($oldid) {
                $sql = $wpdb->prepare("SELECT grampsid FROM {$wpdb->prefix}tangled_web_redir
                                       WHERE tabname=%s AND handle=%s", $tab, $oldid);
                $pid = $wpdb->get_var($sql);
            }
        }

        $jsattrs = ['ajaxurl' => admin_url('admin-ajax.php'),
                    'baseurl' => plugin_dir_url(__FILE__),
                    'title' => trim(wp_title('', false)),
                    'tab' => $tab,
                    'datadir' => str_replace(' ', '%20', $datadir),
                    'what_to_show' => implode(',', $what_to_show),
                    'gonk' => wp_create_nonce('gramps_nonce'),
                    'searchlimit' => 20];
        if ($pid) {
            $jsattrs['pid'] = $pid;
        }

        wp_localize_script('tangled-web-js', 'myAjax', $jsattrs);
        wp_enqueue_script('tangled-web-js');

        if ($pid) {
            return $this->get_pid_html($datadir, $pid, $tab);
        }

        $content = $this->generate_home_page_content($globs, $tab, $datadir, $what_to_show);
        return $this->generate_page($globs, $content, $tab);
    }

    function tangled_web_home()
    {
        $tab = $_REQUEST['tab'];
        if (!$this->check_id_field($tab)) {
            header("HTTP/1.1 418 I'm a teapot");
            die();
        }

        if (isset($_REQUEST['show'])) {
            $what_to_show = $this->check_show_option($_REQUEST['show']);
        }
        else {
            $what_to_show = $this->what_to_show_full;
        }

        $datadir = $this->get_datadir($tab);
        $globs = $this->get_globals($datadir);
        echo $this->generate_home_page_content($globs, $tab, $datadir, $what_to_show);
        die();
    }

    private function check_show_option($showopts)
    {
        $what_to_show = [];
        foreach (explode(',', $showopts) as $what) {
            if (in_array($what, $this->what_to_show_full)) {
                $what_to_show[] = $what;
            }
            else {
                echo "<div>***** Show option $what is not recognized.</div>\n";
            }
        }

        return $what_to_show;
    }

    private function generate_home_page_content($globs, $tab, $datadir, $what_to_show)
    {
        $outstr = '';
        $sep = '';

        foreach ($what_to_show as $show) {

            if ($show == 'photo') {
                $hi = $globs['home_image'];
                if ($hi) {
                    $dirs = $this->get_dir($hi);
                    $home_image = "/{$datadir}/img/{$dirs}/{$hi}";
                    $home_image = str_replace(' ', '%20', $home_image);
                    $outstr .= "$sep<div id=\"home-image\"><img src=\"$home_image\" />\n";
                    if ($globs['home_image_desc']) {
                        $outstr .= "<span id=\"home-image-caption\">{$globs['home_image_desc']}</span>";
                    }
                    $outstr .= "</div>\n";
                }
            }
            elseif ($show == 'note') {
                $home_note = $this->massage_note($tab, $globs['home_note']);
                if ($home_note) {
                    $outstr .= "$sep<div id=\"home-note\">$home_note</div>\n";
                }
            }
            elseif ($show == 'birthdays') {
                $outstr .= $sep . $this->generate_born_on_this_date($globs, $tab);
            }
            elseif ($show == 'cloud') {
                $outstr .= $sep . $this->generate_name_cloud($globs);
            }
            else {
                $outstr .= "$sep<div>***** Directive $show not recognized.</div>\n";
            }
            $sep = '<br>';
        }

        return $outstr;
    }

    private function generate_name_cloud($globs)
    {
        // Compute ranges
        $cloud = $globs['cloud'];
        $max_count = 0;
        $min_count = 99999;
        foreach ($cloud as $nam) {
            $cnt = (int)$nam[1];
            if ($cnt > $max_count) {
                $max_count = $cnt;
            }
            if ($cnt < $min_count) {
                $min_count = $cnt;
            }
        }

        $diff = $max_count - $min_count;
        $range_size = $diff / 8;
        if ($range_size < 1) {
            $range_size = 1;
        }

        shuffle($cloud);
        $name_cloud = '';
        foreach ($cloud as $nam) {
            $cnt = (int)$nam[1];
            $c = intdiv($cnt-$min_count, $range_size);
            $align = rand(1,5);
            $ff = rand(1,5);
            $attrs = "class=\"sz{$c} cld-name al{$align} ff{$ff}\"";
            $namstr = str_replace(' ', '&nbsp;', htmlentities($nam[0]));
            $name_cloud .= "<span {$attrs}>{$namstr}</span> \n";
        }
        return "<div id=\"name-cloud\"><h3>Names</h3>$name_cloud</div>";
    }

    private function generate_born_on_this_date($globs, $tab)
    {
        global $wpdb;
        global $wp;
        $url = '/' . $wp->request;

        $today = date('F j');
        $outstr = "<div id=\"born-this-date\"><h3>Born on this day, $today</h3>\n";

        $sql = $wpdb->prepare('SELECT pid, surname, given, prim, byear '
             . "FROM {$wpdb->prefix}tangled_web_index "
             . 'WHERE tabname=%s AND bdate LIKE %s AND btype="B" '
             . 'ORDER BY bdate;', $tab, ('%-' . date('m-d')));
        $res =  $wpdb->get_results($sql, ARRAY_A);

        $outstr .= '<ul>';
        foreach ($res as $one_bday) {
            if ($one_bday['prim'] == '1') {
                $namelink = ['pid' => $one_bday['pid'],
                             'giv' => $one_bday['given'],
                             'sur' => $one_bday['surname']];
                $name = $this->fmt_name($tab, $url, $namelink);
                $outstr .= "<li>{$one_bday['byear']}: $name</li>\n";
            }
        }
        $outstr .= "</ul></div>\n";
        return $outstr;
    }


    private $not_found_str = '<b>Request data not found.</b>';
    private $birthstr = ['B'=>'Born', 'P'=>'Baptized', ''=>''];
    private $deathstr = ['D'=>'Died', 'B'=>'Buried', 'S'=>'Stillborn', ''=>''];
    private $spouse_type_str = ['M'=>'Wife', 'F'=>'Husband'];

    function get_pid_html($datadir, $pid, $tab)
    {
        $dir = $this->get_dir($pid);
        if (!isset($dir)) {
            return $this->not_found_str;
        }

        $names = $this->get_index_data_by_pid($tab, $pid);
        if (!$names) {
            return $this->not_found_str;
        }

        global $wp;
        $url = '/' . $wp->request;
        $globs = $this->get_globals($datadir);
        $faminfo = $this->get_data_from_file($datadir, 'fam', $dir, $pid);
        $summary = $names[0];
        $plugin_path = plugin_dir_url(__FILE__);
        $datadir = str_replace(' ', '%20', $datadir);

        $out = [];

        $namestr = $summary['given'] . ' ' . $summary['surname'];
        $out[] = '<p><span class="title-name">' . $namestr . '</span></p>';

        $out[] = '<span class="bold">' . $this->birthstr[$summary['btype']] .'</span> ';
        $out[] = $this->get_date_place($summary['bdate'], $summary['bplace']);
        $out[] = '<br/>';

        $out[] = '<span class="bold">' . $this->deathstr[$summary['dtype']] .'</span> ';
        $out[] = $this->get_date_place($summary['ddate'], $summary['dplace']);
        $out[] = '</p>';

        $out[] = '<h3>Families</h3><p>';
        if (array_key_exists('dad', $faminfo['famc'])) {
            $out[] = '<span class="bold">Father:</span> '
                   . $this->fmt_name($tab, $url, $faminfo['famc']['dad'])
                   . '</span>';
        }
        if (array_key_exists('mom', $faminfo['famc'])) {
            $out[] = '<br/><span class="bold">Mother:</span> '
                   . $this->fmt_name($tab, $url, $faminfo['famc']['mom'])
                   . '</span>';
        }
        $out[] = '</p>';

        // For each spouse
        foreach ($faminfo['fams'] as $fams) {
            $out[] = '<span class="bold">' . $this->spouse_type_str[$summary['gender']]
                   . '</span>: '
                   . $this->fmt_name($tab, $url, $fams[0]) . '<br/>';

            $children = $fams[1];
            if (count($children) > 0) {
                $out[] = '<span class="bold">Children:</span><ol>';
                foreach ($children as $child) {
                    $out[] = '<li>' . $this->fmt_name($tab, $url, $child) . '</li>';
                }
                $out[] = '</ol>';
            }
        }

        return $this->generate_page($globs, implode('', $out), $tab);
    }

    private function generate_page($globs, $content, $tab)
    {
        $plugin_path = plugin_dir_url(__FILE__);
        $tstamp = $globs['timestamp'];
        $tstamp = explode('.', $tstamp)[0];
        return <<<PAGE_CONTENT
<div class="tw-main">

<div id="gimage">
<div id="gimage-bar">
<div id="gimage-close"><img src="{$plugin_path}img/cancel.png" alt="close"></div>
<div id="gimage-dl"><img src="{$plugin_path}img/download.png" alt="download"></div>
</div>
<div id="gimage-content"></div>
<div id="gimage-desc"></div>
</div>

<div id="tw-buttons">
<img id="home-button" src="{$plugin_path}img/home.png" alt="Home">
<img id="search-button" src="{$plugin_path}img/search.png" alt="Search">
<div id="search-menu"></div></div>

<div id="tw-content">
$content
</div>

<div class="bottom">Generated {$tstamp} by
<a href="https://github.com/hgboldt/Tangled-Web" target="_blank">Tangled Web</a>
version 0.9.
</div>

</div>
PAGE_CONTENT;
    }

    private function fmt_name($tab, $url, $namelink)
    {
        if (!isset($namelink)) {
            return '';
        }

        if (is_array($namelink)) {
            $vitals = '';
            if (array_key_exists('dat', $namelink)) {
                $vitals = '(' . $namelink['dat'] . ')';
            }

            return '<span class="person">'
                 . '<a class="plnk" href="' . $url
                 . '/?p=' . $namelink['pid'] . '">'
                 . $namelink['giv'] . ' ' . $namelink['sur'] . '</a> '
                 . $vitals . '</span>';
        }

        return '(unknown)';
    }

    private function get_date_place($date, $place)
    {
        $str = '';
        $sep = '';
        if ($date) {
            $str = $date;
            $sep = '; ';
        }
        if ($place) {
            $str .= $sep . $place;
        }
        return $str;
    }

    function get_data_from_file($datadir, $typ, $dir, $pid)
    {
        $filename = ABSPATH . $datadir . '/' . $typ . '/' . $dir . '/' . $pid . '.json';
        $fileh = fopen($filename, 'r');
        $info = null;
        if ($fileh) {
            $infostr = fgets($fileh);
            if ($infostr) {
                $info = json_decode($infostr, true);
            }
        }
        fclose($fileh);
        return $info;
    }

    function massage_note($tab, $note)
    {
        //
        // Convert [id|name] tags to clickable links.
        //
        global $wp;
        $url = '/' . $wp->request;

        $count = preg_match_all("/\[.*?\]/", $note, $matches);
        if ($count > 0)
        {
            foreach ($matches[0] as $match)
            {
                $m = explode('|', substr($match,1,-1));
                $pid = sanitize_text_field($m[0]);
                $name = sanitize_text_field($m[1]);
                if (isset($pid)) {
                    $a = '<a class="plnk" href="' . $url
                       . '?p=' . $pid . '">'
                       . $name . '</a>';
                    $note = str_replace($match, $a, $note);
                }
                else {
                    $note = str_replace($match, $name, $note);
                }
            }
        }
        return $note;
    }

    function get_dir($pid)
    {
        $pnum = intval(preg_replace('/[^0-9]/', '', $pid));
        $dir1 = chr(ord('a') + ($pnum % NUM_SUBDIRS));
        $dir2 = chr(ord('a') + (intdiv($pnum, NUM_SUBDIRS) % NUM_SUBDIRS));
        return $dir1 . '/' . $dir2;
    }

    private function get_datadir($tab)
    {
        global $wpdb;
        $sql = $wpdb->prepare("SELECT datadir FROM {$wpdb->prefix}tangled_web_data
                               WHERE tabname=%s", $tab);
        return $wpdb->get_var($sql);
    }

    function get_index_data_by_pid($tab, $pid)
    {
        global $wpdb;
        $sql = $wpdb->prepare("SELECT * FROM {$wpdb->prefix}tangled_web_index "
             . 'WHERE tabname=%s AND pid=%s ORDER BY prim DESC;', $tab, $pid);
        return $wpdb->get_results($sql, ARRAY_A);
    }

    function get_globals($datadir)
    {
        $globs = [];
        $filename = ABSPATH . $datadir . '/globs.json';
        $fileh = fopen($filename, 'r');
        if ($fileh) {
            $globstr = fgets($fileh);
            if ($globstr) {
                $globs = json_decode($globstr, true);
            }
            fclose($fileh);
        }
        return $globs;
    }

    function validate_number($str)
    {
        if (is_numeric($str)) {
            return $str;
        }
        return 0;
    }

    //------------------//
    //                  //
    //   S E A R C H    //
    //                  //
    //------------------//

    function tangled_web_search()
    {
        global $wpdb;

        if (isset($_REQUEST['email'])) {
            header("HTTP/1.1 418 I'm a teapot");
            die();
        }

        if (!isset($_REQUEST['action'])
        ||  $_REQUEST['action'] != 'tangled_web_search'
        ||  !isset($_REQUEST['gonk'])
        ||  !wp_verify_nonce($_REQUEST['gonk'], 'gramps_nonce')) {
            header("HTTP/1.1 418 I'm a teapot");
            die();
        }

        $tab = $_REQUEST['table_id'];
        if (!$this->check_id_field($tab)) {
            header("HTTP/1.1 418 I'm a teapot");
            die();
        }

        $surname = isset($_REQUEST['surname']) ? $_REQUEST['surname'] : '';
        $given = isset($_REQUEST['given']) ? $_REQUEST['given'] : '';
        $place = isset($_REQUEST['place']) ? $_REQUEST['place'] : '';
        $yearfrom = isset($_REQUEST['yearfrom']) ? $this->validate_number($_REQUEST['yearfrom']) : '';
        $yearto = isset($_REQUEST['yearto']) ? $this->validate_number($_REQUEST['yearto']) : '';
        $orderby = isset($_REQUEST['orderby']) ? $_REQUEST['orderby'] : '';
        $orderseq = isset($_REQUEST['orderseq']) ? $_REQUEST['orderseq'] : '';

        $have_offset = isset($_REQUEST['offset']);
        $offset = $have_offset ? $_REQUEST['offset'] : 0;

        $search_crit = [
                'surname' => $surname,
                'given' => $given,
                'place' => $place,
                'yearfrom' => $yearfrom,
                'yearto' => $yearto,
                'offset' => $offset,
                'orderby' => $orderby,
                'orderseq' => $orderseq
            ];

        $where = 'WHERE tabname=%s ';
        $sqlargs = ["{$tab}"];

        if ($surname) {
            $sqlargs[] = "%{$surname}%";
            $where .= "AND surname LIKE %s ";
        }

        if ($given) {
            $sqlargs[] = "%{$given}%";
            $where .= "AND given LIKE %s ";
        }

        if ($place) {
            $sqlargs[] = "%{$place}%";
            $sqlargs[] = "%{$place}%";
            $where .= "AND (bplace LIKE %s OR dplace LIKE %s) ";
        }

        if ($yearfrom && $yearto) {
            $sqlargs[] = $yearto;
            $sqlargs[] = $yearfrom;
            $where .= "AND (byear <= %s AND dyear >= %s) ";
        }
        elseif ($yearfrom) {
            $sqlargs[] = $yearfrom;
            $where .= "AND dyear >= %s ";
        }
        elseif ($yearto) {
            $sqlargs[] = $yearto;
            $where .= "AND byear <= %s ";
        }

        $orderstr = '';
        if ($orderby) {
            $seq = '';
            if ($orderseq == 'D') {
                $seq = ' DESC';
            }

            $orderstr = '';
            if ($orderby == 'byear') {
                $orderstr = "ORDER BY byear{$seq}, bdate{$seq} ";
            }
            elseif ($orderby == 'dyear') {
                $orderstr = "ORDER BY dyear{$seq}, ddate{$seq} ";
            }
            elseif ($orderby == 'surname') {
                $orderstr = "ORDER BY surname{$seq}, given{$seq} ";
            }
            elseif ($orderby == 'given') {
                $orderstr = "ORDER BY given{$seq}, surname{$seq} ";
            }
            elseif ($orderby == 'bplace') {
                $orderstr = "ORDER BY bplace{$seq}, byear{$seq} ";
            }
            elseif ($orderby == 'dplace') {
                $orderstr = "ORDER BY dplace{$seq}, byear{$seq} ";
            }
        }

        $sqlfrom = "FROM {$wpdb->prefix}tangled_web_index $where";

        // Get count of items in table (if we don't have an offset)
        $row_count = -1;
        $more = 0;
        if (!$have_offset) {
            $sql = $wpdb->prepare("SELECT COUNT(*) $sqlfrom LIMIT 401;", $sqlargs);
            $row_count = $wpdb->get_var($sql);
            if ($row_count > 400) {
                $row_count = 400;
                $more = 1;
            }
        }

        // Get summary data and names
        $offset_query = '';
        if ($have_offset) {
            $sqlargs[] = $offset;
            $offset_query = "OFFSET %d ";
        }

        $sql = $wpdb->prepare("SELECT pid, surname, given, "
             . "bdate, bplace, ddate, dplace  "
             . $sqlfrom . $orderstr
             . "LIMIT 20 "
             . $offset_query . ";", $sqlargs);
        $query_results = $wpdb->get_results($sql, ARRAY_A);

        $datadir = str_replace(' ', '%20', get_option('tangled_web_datadir'));
        $result = ['search' => $search_crit,
                   'gonk' => wp_create_nonce('gramps_nonce'),
                   'dir' => $datadir,
                   'result' => $query_results];

        if ($row_count >= 0) {
            $result['count'] = $row_count;
            $result['more'] = $more;
        }

        if (!empty($_SERVER['HTTP_X_REQUESTED_WITH'])
        &&  strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) == 'xmlhttprequest') {
           $result = json_encode($result);
           echo $result;
        }
        else {
           header("Location: ".$_SERVER["HTTP_REFERER"]);
        }

        die();
    }

    //------------------//
    //                  //
    //   A P I s        //
    //                  //
    //------------------//

    function my_update_cookie($logged_in_cookie)
    {
        $_COOKIE[LOGGED_IN_COOKIE] = $logged_in_cookie;
    }


    function tangled_web_start(WP_REST_Request $request)
    {
        global $wpdb;

        add_action('set_logged_in_cookie', [$this, 'my_update_cookie']);

        $creds = ['user_login' => $request->get_param('id'),
                  'user_password' => $request->get_param('pw'),
                  'remember' => true];

        $user = wp_signon($creds, false);
        if (is_wp_error($user)) {
            return $user;
        }

        wp_set_current_user($user->ID);
        wp_set_auth_cookie($user->ID);
        $nonce = wp_create_nonce('wp_rest');

        $sql = "SELECT tabname, last_update FROM {$wpdb->prefix}tangled_web_data";
        $res = $wpdb->get_results($sql, ARRAY_A);
        if (count($res) == 0) {
            return new WP_Error('no_table', 'No entries in table', ['status' => 404]);
        }

        $retval = ['gonk' => $nonce,
                   'tables' => $res,
                   'user' => $user->to_array()];
        return new WP_REST_Response($retval);
    }


    function tangled_web_status(WP_REST_Request $request)
    {
        global $wpdb;

        $tab = $request->get_param('tab');

        $sql = $wpdb->prepare("SELECT pid, csi, csf FROM {$wpdb->prefix}tangled_web_index
                               WHERE tabname=%s", $tab);
        $res = $wpdb->get_results($sql, ARRAY_A);

        if (count($res) == 0) {
            return new WP_Error('no_table', 'No entries in table', ['status' => 404]);
        }

        return new WP_REST_Response(['checksums' => $res ]);
    }

}

function activate_plugin_gramps()
{
    global $wpdb;

    if (!current_user_can('activate_plugins'))
    {
        return;
    }

    $prefix = $wpdb->prefix;
    $charset_collate = $wpdb->get_charset_collate();

    $wpdb->query("DROP TABLE IF EXISTS {$wpdb->prefix}tangled_web_redir");
    $wpdb->query("DROP TABLE IF EXISTS {$wpdb->prefix}tangled_web_index");
    $wpdb->query("DROP TABLE IF EXISTS {$wpdb->prefix}tangled_web_data");

    $sql = "CREATE TABLE {$wpdb->prefix}tangled_web_data (
                tabname VARCHAR(10) PRIMARY KEY,
                datadir VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL,
                redir_status VARCHAR(20) NOT NULL,
                last_update TIMESTAMP NOT NULL
            ) $charset_collate";
    dbDelta($sql);

    $sql = "CREATE TABLE {$wpdb->prefix}tangled_web_index (
                id INTEGER NOT NULL,
                tabname VARCHAR(10) NOT NULL,
                pid VARCHAR(10) NOT NULL,
                surname VARCHAR(50) NOT NULL,
                given VARCHAR(50) NOT NULL,
                gender CHAR(1) NOT NULL,
                prim CHAR(1) NOT NULL,
                bplace VARCHAR(50),
                btype CHAR(1),
                bdate CHAR(40),
                byear CHAR(4),
                dplace VARCHAR(50),
                dtype CHAR(1),
                ddate CHAR(40),
                dyear CHAR(4),
                csi VARCHAR(6),
                csf VARCHAR(6),
                CONSTRAINT `fk_index_tabname`
                    FOREIGN KEY (tabname)
                    REFERENCES {$wpdb->prefix}tangled_web_data (tabname)
                    ON DELETE CASCADE
           ) $charset_collate;";
    dbDelta($sql);

    $sql = "CREATE TABLE {$wpdb->prefix}tangled_web_redir (
                handle VARCHAR(50) PRIMARY KEY,
                tabname VARCHAR(10) NOT NULL,
                grampsid VARCHAR(10) NOT NULL,
                CONSTRAINT `fk_redir_tabname`
                    FOREIGN KEY (tabname)
                    REFERENCES {$wpdb->prefix}tangled_web_data (tabname)
                    ON DELETE CASCADE
            ) $charset_collate";
    dbDelta($sql);

    update_option('tangled_web_indexes', '');
}

function tangled_web_init()
{
    global $tw_instance;
    $tw_instance = new TangledWeb();
}

register_activation_hook(__FILE__, 'activate_plugin_gramps');
add_action('init', 'tangled_web_init');

?>
