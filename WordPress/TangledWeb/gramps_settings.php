<?php

        if (isset($_POST['updated']) && $_POST['updated'] === 'true' )
        {
            $this->handle_form();
        }

        $datadir = get_option('gramps_settings_datadir');
        ?>
        <div>
            <h2>Gramps Settings</h2>
            <form id="gramps-settings" method="POST">
                <input type="hidden" name="updated" value="true" />
                <?php wp_nonce_field('gramps_update', 'gramps_form'); ?>
                <table class="form-table">
                    <tbody>
                        <tr>
                            <th><label for="datadir">Data directory</label></th>
                            <td><input name="datadir" id="datadir" type="text"
                                       value="<?php echo $datadir; ?>"
                                       class="input-text" /></td>
                        </tr>
                    </tbody>
                </table>
            </form>
            <button type="submit" form="gramps-settings value="Submit">Submit</button>
        </div>



?>