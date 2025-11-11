@app.route('/dork', methods=['GET', 'POST'])
@login_required
def dork_search():
    if request.method == 'POST':
        dork_query = request.form.get('dork_query')
        search_engine = request.form.get('engine', 'google')
        max_results = int(request.form.get('max_results', 50))
        
        # Validate max results
        if max_results > Config.DORK_MAX_RESULTS:
            max_results = Config.DORK_MAX_RESULTS
        
        try:
            # Perform dork search
            if search_engine == 'google':
                dork = GoogleDork()
            else:
                dork = YandexDork()
            
            flash('Searching... This may take a few minutes.', 'info')
            urls = dork.search(dork_query, max_results)
            
            # Eğer sonuç yoksa demo URL'leri göster
            if not urls:
                flash('No results found from search engine. Showing demo vulnerable URLs for testing.', 'warning')
                from dork_engine import DEMO_URLS
                urls = DEMO_URLS
            
            # Save to database
            dork_id = db.save_dork_results(dork_query, search_engine, urls)
            
            flash(f'Found {len(urls)} URLs!', 'success')
            return render_template('dork_results.html', urls=urls, dork_query=dork_query)
        
        except Exception as e:
            flash(f'Error during search: {str(e)}', 'danger')
            print(f"[!] Dork search error: {e}")
            import traceback
            traceback.print_exc()
            return redirect(url_for('dork_search'))
    
    return render_template('dork.html', predefined_dorks=SQL_DORKS)
