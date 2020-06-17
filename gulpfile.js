var gulp = require('gulp');
var source = require('vinyl-source-stream'); // Used to stream bundle for further handling
var browserify = require('browserify');
var watchify = require('watchify');
var babelify = require('babelify');
var gulpif = require('gulp-if');
var uglify = require('gulp-uglify');
var streamify = require('gulp-streamify');
var notify = require('gulp-notify');
var concat = require('gulp-concat');
var cleancss = require('gulp-clean-css');
var log = require('fancy-log');
var rename = require("gulp-rename");
var less = require('gulp-less');
var glob = require('glob');
var path = require('path');
var livereload = require('gulp-livereload');
var modernizr = require('gulp-modernizr');
var mocha = require('gulp-mocha');
var istanbul = require('gulp-istanbul');
var isparta = require('isparta');
var coverageEnforcer = require('gulp-istanbul-enforcer');
// Note: this touch only updates the modtime of an existing file, but will never
// create an empty file (unlike the command-line "touch").
var touch = require('gulp-touch-fd');
var spawn = require('child_process').spawn;
var argv = require('yargs')
  .default('port', 8000)
  .default('address', 'localhost')
  .argv;

// External dependencies you do not want to rebundle while developing,
// but include in your application deployment
var dependencies = [
];

var options = {
  src: './cc_licenses/static/js/index.js',
  dest: './cc_licenses/static/js/',

  modernizr: {
    src: './cc_licenses/static/js/index.js',
    dest: './cc_licenses/static/libs/',
  },

  css: {
    src: './cc_licenses/static/less/index.less',
    watch: './cc_licenses/static/less/**/*.less',
    dest: './cc_licenses/static/css/'
  },
  development: false
}

if (argv._ && argv._[0] === 'deploy') {
  options.development = false
} else {
  options.development = true
}

if (options.development) {
  console.log("Building for development")
  delete process.env['NODE_ENV'];
} else {
  console.log("Building for production")
  process.env['NODE_ENV'] = 'production';
}

gulp.task('modernizr', function() {
  return gulp.src(options.modernizr.src)
        .pipe(modernizr())
        .pipe(gulpif(!options.development, streamify(uglify())))
        .pipe(gulp.dest(options.modernizr.dest))
        .pipe(touch())
})

var browserifyTask = function () {

  // Our app bundler
  var appBundler = browserify({
    entries: [options.src], // Only need initial file, browserify finds the rest
    transform: [babelify], // We want to convert JSX to normal javascript
    debug: options.development, // Gives us sourcemapping
    cache: {}, packageCache: {}, fullPaths: options.development // Requirement of watchify
  });

  // We set our dependencies as externals on our app bundler when developing
  (options.development ? dependencies : []).forEach(function (dep) {
    appBundler.external(dep);
  });

  // The rebundle process
  var rebundle = function () {
    var start = Date.now();
    console.log('Building APP bundle');
    return appBundler.bundle()
        .on('error', log)
        .pipe(source('index.js'))
        .pipe(gulpif(!options.development, streamify(uglify())))
        .pipe(rename('bundle.js'))
        .pipe(gulp.dest(options.dest))
        .pipe(gulpif(options.development, livereload()))
        .pipe(touch())
        .pipe(notify(function () {
          console.log('APP bundle built in ' + (Date.now() - start) + 'ms');
        }));
  };

  // Fire up Watchify when developing
  if (options.development) {
    var watcher = watchify(appBundler);
    watcher.on('update', rebundle);
  }

  // We create a separate bundle for our dependencies as they
  // should not rebundle on file changes. This only happens when
  // we develop. When deploying the dependencies will be included
  // in the application bundle
  if (options.development) {

    var vendorsBundler = browserify({
      debug: true,
      require: dependencies
    });

    // Run the vendor bundle
    var start = new Date();
    console.log('Building VENDORS bundle');
    vendorsBundler.bundle()
      .on('error', log)
      .pipe(source('vendors.js'))
      .pipe(gulpif(!options.development, streamify(uglify())))
      .pipe(gulp.dest(options.dest))
      .pipe(touch())
      .pipe(notify(function () {
        console.log('VENDORS bundle built in ' + (Date.now() - start) + 'ms');
      }));
  }

  return rebundle();
};
gulp.task('browserify', gulp.series('modernizr', browserifyTask));

var cssTask = function () {
    var lessOpts = {
      relativeUrls: true,
    };
    if (options.development) {
      var run = function () {
        var start = Date.now();
        console.log('Building CSS bundle');
        return gulp.src(options.css.src)
          .pipe(gulpif(options.development, livereload()))
          .pipe(concat('index.less'))
          .pipe(less(lessOpts))
          .pipe(rename('bundle.css'))
          .pipe(gulp.dest(options.css.dest))
          .pipe(touch())
          .pipe(notify(function () {
            console.log('CSS bundle built in ' + (Date.now() - start) + 'ms');
          }));
      };
      gulp.watch(options.css.watch, run);
      return run();
    } else {
      return gulp.src(options.css.src)
        .pipe(concat('index.less'))
        .pipe(less(lessOpts))
        .pipe(rename('bundle.css'))
        .pipe(cleancss())
        .pipe(gulp.dest(options.css.dest))
        .pipe(touch())
    }
};
gulp.task('css', cssTask);

gulp.task('rebuild', gulp.parallel('css', 'browserify'))

function start_dev_server(done) {
  console.log("Starting Django runserver http://"+argv.address+":"+argv.port+"/");
  var args = ["manage.py", "runserver", argv.address+":"+argv.port];
  // Newer versions of npm mess with the PATH, sometimes putting /usr/bin at the front,
  // so make sure we invoke the python from our virtual env explicitly.
  var python = process.env['VIRTUAL_ENV'] + '/bin/python';
  var runserver = spawn(python, args, {
    stdio: "inherit",
  });
  runserver.on('close', function(code) {
    if (code !== 0) {
      console.error('Django runserver exited with error code: ' + code);
    } else {
      console.log('Django runserver exited normally.');
    }
  });
  done();
}
gulp.task('start_dev_server', gulp.series('rebuild', start_dev_server))

// Starts our development workflow
gulp.task('default', gulp.series('start_dev_server', function (done) {
  livereload.listen();
  done();
}));

gulp.task('deploy', gulp.series('rebuild'))

gulp.task('test', gulp.series(function () {
  require('babel-core/register');
  return gulp
    .src('./cc_licenses/static/js/app/**/*.js')
    .pipe(istanbul({
      instrumenter: isparta.Instrumenter
      , includeUntested: true
    }))
    .pipe(istanbul.hookRequire())
    .on('finish', function () {
      gulp
        .src('./cc_licenses/static/js/test/**/test_*.js', {read: false})
        .pipe(mocha({
          require: [
            'jsdom-global/register'
          ]
        }))
        .pipe(istanbul.writeReports({
          dir: './coverage/'
          , reportOpts: {
            dir: './coverage/'
          }
          , reporters: [
            'text'
            , 'text-summary'
            , 'json'
            , 'html'
          ]
        }))
        .pipe(coverageEnforcer({
          thresholds: {
            statements: 80
            , branches: 50
            , lines: 80
            , functions: 50
          }
          , coverageDirectory: './coverage/'
          , rootDirectory: ''
        }))
      ;
    })
  ;
}));
