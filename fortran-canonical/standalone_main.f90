! Standalone main program for DW-NOMINATE Fortran
! Reads CSV vote matrices and calls dwnom() subroutine directly
! Replaces the R wrapper for clean scientific comparison against C++
!
! Usage: dwnominate_fortran <input_dir> <output_dir> <niter> <model> &
!        [state_dir] [fit|evaluate] [iteration_start]

program dwnominate_standalone
  use xxcom_mod, only: core_xdata => XDATA, core_zmid => ZMID, &
                       core_dyn => DYN, core_weight => WEIGHT, &
                       core_xbiglog => XBIGLOG, core_kbiglog => KBIGLOG
  implicit none

  ! Parameters
  integer, parameter :: MAX_LEGS = 1000
  integer, parameter :: MAX_RCS = 5000
  integer, parameter :: MAX_DIM = 2

  ! NOMSTARTIN: [NS, NMODEL, NFIRST, NLAST, IHAPPY1, IHAPPY2]
  integer :: NOMSTARTIN(6)

  ! Input arrays
  double precision, allocatable :: WEIGHTSIN(:)
  double precision, allocatable :: DYNIN(:,:), ZMIDIN(:,:)
  double precision, allocatable :: XDATAIN(:,:)
  integer, allocatable :: ICONGIN(:), MCONGIN(:,:)
  integer, allocatable :: NCONGIN(:), ID1IN(:)
  integer, allocatable :: RCVOTE1IN(:,:), RCVOTE9IN(:,:)
  integer, allocatable :: RCVOTET1IN(:,:), RCVOTET9IN(:,:)

  ! Output arrays
  double precision, allocatable :: XDATAOUT(:,:)
  double precision, allocatable :: SDX1OUT(:), SDX2OUT(:)
  double precision, allocatable :: VARX1OUT(:), VARX2OUT(:)
  double precision, allocatable :: XBIGLOGOUT(:,:)
  integer, allocatable :: KBIGLOGOUT(:,:)
  double precision, allocatable :: GMPAOUT(:), GMPBOUT(:)
  double precision, allocatable :: DYNOUT(:,:), ZMIDOUT(:,:)
  double precision, allocatable :: WEIGHTSOUT(:)

  ! Local variables
  integer :: NS, NMODEL, NFIRST, NLAST, NITER, iteration_start
  integer :: terminal_iteration, state_iterations
  integer :: num_periods, total_legs, total_rcs
  integer :: i, j, p, rc_offset, leg_offset
  integer :: num_legs_in_period, num_rcs_in_period
  integer :: vote_code
  character(len=512) :: input_dir, output_dir, state_dir, fname
  character(len=512) :: arg
  character(len=65536) :: line
  integer :: argc, ios, unit_num
  logical :: evaluate_only
  real :: native_plog

  ! Timing
  real :: start_time, end_time

  ! Defaults
  input_dir = 'test_single'
  output_dir = 'comparison/fortran_niter1'
  NITER = 1
  iteration_start = 1
  NS = 2
  NMODEL = 0
  state_dir = ''
  evaluate_only = .false.
  state_iterations = -1

  ! Parse command line arguments
  argc = command_argument_count()
  if (argc >= 1) call get_command_argument(1, input_dir)
  if (argc >= 2) call get_command_argument(2, output_dir)
  if (argc >= 3) then
    call get_command_argument(3, arg)
    read(arg, *) NITER
  endif
  if (argc >= 4) then
    call get_command_argument(4, arg)
    read(arg, *) NMODEL
  endif
  if (argc >= 5) call get_command_argument(5, state_dir)
  if (argc >= 6) then
    call get_command_argument(6, arg)
    evaluate_only = trim(adjustl(arg)) == 'evaluate'
  endif
  if (argc >= 7) then
    call get_command_argument(7, arg)
    read(arg, *) iteration_start
  endif

  if (NITER < 0 .or. iteration_start < 1) then
    write(*,*) 'ERROR: niter must be non-negative and iteration_start positive'
    stop 1
  endif

  write(*,*) '============================================'
  write(*,*) '  DW-NOMINATE Fortran Standalone'
  write(*,*) '============================================'
  write(*,*) '  Input:  ', trim(input_dir)
  write(*,*) '  Output: ', trim(output_dir)
  write(*,*) '  Iterations: ', NITER
  write(*,*) '  Iteration start: ', iteration_start
  write(*,*) '  Model: ', NMODEL
  if (len_trim(state_dir) > 0) write(*,*) '  State: ', trim(state_dir)
  if (evaluate_only) write(*,*) '  Mode: native PLOG evaluation only'
  write(*,*) ''

  call cpu_time(start_time)

  ! Step 1: Detect number of periods by counting votes_matrix_p*.csv files
  block
    logical :: fexists
    num_periods = 0
    do i = 1, 100
      write(fname, '(A,A,I0,A)') trim(input_dir), '/votes_matrix_p', i, '.csv'
      inquire(file=trim(fname), exist=fexists)
      if (fexists) then
        num_periods = i
      else
        exit
      endif
    enddo
  end block
  write(*,*) '  Detected periods: ', num_periods

  if (num_periods == 0) then
    write(*,*) 'ERROR: No vote matrix files found in ', trim(input_dir)
    stop 1
  endif

  ! Step 2: Read vote matrices and count dimensions
  ! First pass: count legislators and roll calls per period
  call count_data(input_dir, num_periods, total_legs, total_rcs)

  write(*,*) '  Total legislators: ', total_legs
  write(*,*) '  Total roll calls: ', total_rcs

  ! Step 3: Allocate arrays
  NFIRST = 1
  NLAST = num_periods

  allocate(WEIGHTSIN(NS + 1))
  allocate(DYNIN(total_rcs, NS))
  allocate(ZMIDIN(total_rcs, NS))
  allocate(ICONGIN(total_rcs))
  allocate(MCONGIN(num_periods, 3))
  allocate(NCONGIN(total_legs))
  allocate(ID1IN(total_legs))
  allocate(XDATAIN(total_legs, NS))
  allocate(RCVOTE1IN(total_legs, total_rcs))
  allocate(RCVOTE9IN(total_legs, total_rcs))
  allocate(RCVOTET1IN(total_rcs, total_legs))
  allocate(RCVOTET9IN(total_rcs, total_legs))

  allocate(XDATAOUT(total_legs, NS))
  allocate(SDX1OUT(total_legs))
  allocate(SDX2OUT(total_legs))
  allocate(VARX1OUT(total_legs))
  allocate(VARX2OUT(total_legs))
  allocate(XBIGLOGOUT(total_legs, 2))
  allocate(KBIGLOGOUT(total_legs, 4))
  allocate(GMPAOUT(total_legs))
  allocate(GMPBOUT(total_legs))
  allocate(DYNOUT(total_rcs, NS))
  allocate(ZMIDOUT(total_rcs, NS))
  allocate(WEIGHTSOUT(NS + 1))

  XDATAOUT = 0.0d0
  SDX1OUT = 0.0d0
  SDX2OUT = 0.0d0
  VARX1OUT = 0.0d0
  VARX2OUT = 0.0d0
  XBIGLOGOUT = 0.0d0
  KBIGLOGOUT = 0
  GMPAOUT = 0.0d0
  GMPBOUT = 0.0d0
  DYNOUT = 0.0d0
  ZMIDOUT = 0.0d0
  WEIGHTSOUT = 0.0d0

  ! Step 4: Initialize
  WEIGHTSIN(1) = 1.0d0    ! W1
  WEIGHTSIN(2) = 0.3463d0 ! W2
  WEIGHTSIN(3) = 5.9539d0 ! Beta

  ! Canonical initialization: both alternatives coincide until CUTPLANE.
  DYNIN = 0.0d0   ! Default spread
  ZMIDIN = 0.0d0  ! Default midpoints

  NOMSTARTIN(1) = NS
  NOMSTARTIN(2) = NMODEL
  NOMSTARTIN(3) = NFIRST
  NOMSTARTIN(4) = NLAST
  NOMSTARTIN(5) = iteration_start
  NOMSTARTIN(6) = iteration_start + NITER - 1
  terminal_iteration = NOMSTARTIN(6)

  if (evaluate_only) then
    ! Initialise the canonical COMMON/module state without executing an
    ! optimisation cycle. PLOG is invoked explicitly after dwnom returns.
    NOMSTARTIN(5) = 1
    NOMSTARTIN(6) = 0
    terminal_iteration = iteration_start - 1
  endif

  ! Step 5: Load data
  call load_data(input_dir, num_periods, total_legs, total_rcs, NS, &
                 RCVOTE1IN, RCVOTE9IN, RCVOTET1IN, RCVOTET9IN, &
                 ICONGIN, NCONGIN, ID1IN, XDATAIN, MCONGIN)

  if (len_trim(state_dir) > 0) then
    call load_terminal_state(state_dir, total_legs, total_rcs, NS, &
                             ID1IN, NCONGIN, XDATAIN, ZMIDIN, DYNIN, &
                             WEIGHTSIN, state_iterations)
    if (evaluate_only .and. state_iterations >= 0) then
      terminal_iteration = state_iterations
    else if (.not. evaluate_only .and. argc < 7 .and. &
             state_iterations >= 0) then
      iteration_start = state_iterations + 1
      NOMSTARTIN(5) = iteration_start
      NOMSTARTIN(6) = iteration_start + NITER - 1
      terminal_iteration = NOMSTARTIN(6)
    endif
  else if (evaluate_only) then
    write(*,*) 'ERROR: evaluate mode requires state_dir'
    stop 1
  endif

  write(*,*) ''
  write(*,*) '  Running DW-NOMINATE...'

  ! Step 6: Call dwnom
  call dwnom(NOMSTARTIN, WEIGHTSIN, total_rcs, ICONGIN, DYNIN, &
             ZMIDIN, MCONGIN, total_rcs, total_legs, RCVOTET1IN, RCVOTET9IN, &
             total_legs, NCONGIN, ID1IN, XDATAIN, total_legs, total_rcs, &
             RCVOTE1IN, RCVOTE9IN, XDATAOUT, SDX1OUT, SDX2OUT, VARX1OUT, &
             VARX2OUT, XBIGLOGOUT, KBIGLOGOUT, GMPAOUT, GMPBOUT, DYNOUT, &
             ZMIDOUT, WEIGHTSOUT)

  if (evaluate_only) then
    call PLOG(native_plog, NFIRST, NLAST)
    XDATAOUT = core_xdata(1:total_legs, 1:NS)
    ZMIDOUT = core_zmid(1:total_rcs, 1:NS)
    DYNOUT = core_dyn(1:total_rcs, 1:NS)
    WEIGHTSOUT = core_weight(1:NS + 1)
    XBIGLOGOUT = core_xbiglog(1:total_legs, 1:2)
    KBIGLOGOUT = core_kbiglog(1:total_legs, 1:4)
  endif

  call cpu_time(end_time)

  ! Step 7: Export results
  write(*,*) ''
  write(*,*) '  Results:'
  write(*,'(A,F12.4)') '    W2: ', WEIGHTSOUT(2)
  write(*,'(A,F12.4)') '    Beta: ', WEIGHTSOUT(NS+1)
  write(*,'(A,F8.1,A)') '    Time: ', end_time - start_time, 's'

  call export_results(output_dir, total_legs, total_rcs, NS, num_periods, &
                      XDATAOUT, ZMIDOUT, DYNOUT, WEIGHTSOUT, &
                      ID1IN, NCONGIN, XBIGLOGOUT, KBIGLOGOUT, &
                      terminal_iteration, NMODEL)

  write(*,*) ''
  write(*,*) '  Done.'

contains

  subroutine count_data(dir, nper, tot_legs, tot_rcs)
    character(len=*), intent(in) :: dir
    integer, intent(in) :: nper
    integer, intent(out) :: tot_legs, tot_rcs
    character(len=512) :: fn
    character(len=65536) :: line
    integer :: p, nrc, nleg, ios, u

    tot_rcs = 0
    tot_legs = 0

    do p = 1, nper
      write(fn, '(A,A,I0,A)') trim(dir), '/votes_matrix_p', p, '.csv'
      u = 20 + p
      open(unit=u, file=trim(fn), status='old', action='read', iostat=ios)
      if (ios /= 0) then
        write(*,*) 'ERROR: Cannot open ', trim(fn)
        stop 1
      endif

      ! Count columns from header (= number of roll calls)
      read(u, '(A)') line
      nrc = count_commas(line)  ! number of commas = number of roll calls

      ! Count data rows (= number of legislators)
      nleg = 0
      do
        read(u, '(A)', iostat=ios) line
        if (ios /= 0) exit
        if (len_trim(line) > 0 .and. row_has_observed_vote(line)) then
          nleg = nleg + 1
        endif
      enddo
      close(u)

      tot_rcs = tot_rcs + nrc
      tot_legs = tot_legs + nleg

      write(*,'(A,I2,A,I4,A,I6)') '    Period ', p, ': ', nleg, ' legislators x ', nrc, ' roll calls'
    enddo

    ! XDATA/ID1/NCONG are stacked member-period rows in the canonical caller.
    ! Reusing one unified roster here overwrites NCONG and corrupts every
    ! dynamic period after the first.
  end subroutine

  integer function count_commas(str)
    character(len=*), intent(in) :: str
    integer :: i
    count_commas = 0
    do i = 1, len_trim(str)
      if (str(i:i) == ',') count_commas = count_commas + 1
    enddo
  end function

  logical function row_has_observed_vote(str)
    character(len=*), intent(in) :: str
    character(len=20) :: field
    integer :: start_pos, comma_pos, ios, vote

    row_has_observed_vote = .false.
    comma_pos = index(str, ',')
    if (comma_pos == 0) return
    start_pos = comma_pos + 1
    do while (start_pos <= len_trim(str))
      comma_pos = index(str(start_pos:), ',')
      if (comma_pos == 0) then
        field = str(start_pos:)
      else
        field = str(start_pos:start_pos+comma_pos-2)
      endif
      read(field, *, iostat=ios) vote
      if (ios == 0 .and. vote >= 1 .and. vote <= 6) then
        row_has_observed_vote = .true.
        return
      endif
      if (comma_pos == 0) exit
      start_pos = start_pos + comma_pos
    enddo
  end function

  subroutine load_data(dir, nper, nlegs, nrcs, ndim, &
                       rv1, rv9, rvt1, rvt9, &
                       icong, ncong, id1, xdata, mcong)
    character(len=*), intent(in) :: dir
    integer, intent(in) :: nper, nlegs, nrcs, ndim
    integer, intent(out) :: rv1(nlegs, nrcs), rv9(nlegs, nrcs)
    integer, intent(out) :: rvt1(nrcs, nlegs), rvt9(nrcs, nlegs)
    integer, intent(out) :: icong(nrcs), ncong(nlegs), id1(nlegs)
    double precision, intent(out) :: xdata(nlegs, ndim)
    integer, intent(out) :: mcong(nper, 3)

    character(len=512) :: fn
    character(len=65536) :: line
    character(len=20) :: token
    character(len=64) :: id_token
    integer :: p, i, j, u, ios, rc_off, leg_off, row_index, vote, leg_id
    integer :: nrc_period, nleg_period, comma_pos, start_pos

    ! Initialize
    rv1 = 0
    rv9 = 1
    rvt1 = 0
    rvt9 = 1
    xdata = 0.0d0

    rc_off = 0
    leg_off = 0

    do p = 1, nper
      write(fn, '(A,A,I0,A)') trim(dir), '/votes_matrix_p', p, '.csv'
      u = 20 + p
      open(unit=u, file=trim(fn), status='old', action='read', iostat=ios)

      ! Skip header
      read(u, '(A)') line
      nrc_period = count_commas(line)

      ! Read and stack only member-period rows with an observed vote.
      nleg_period = 0
      do
        read(u, '(A)', iostat=ios) line
        if (ios /= 0) exit
        if (.not. row_has_observed_vote(line)) cycle
        nleg_period = nleg_period + 1
        row_index = leg_off + nleg_period

        ! Parse: first field is legislator_id, rest are votes
        start_pos = 1
        comma_pos = index(line(start_pos:), ',')
        ! R's write.csv() quotes row names, while the Chile audit inputs do
        ! not.  Accept both encodings so exported legislator identifiers are
        ! stable and terminal states remain reloadable across data sources.
        id_token = adjustl(line(1:comma_pos-1))
        if (len_trim(id_token) >= 2 .and. id_token(1:1) == '"') then
          id_token = id_token(2:len_trim(id_token)-1)
        endif
        read(id_token, *, iostat=ios) leg_id
        if (ios /= 0) then
          write(*,*) 'ERROR: invalid legislator identifier: ', &
                     trim(line(1:comma_pos-1))
          stop 1
        endif
        id1(row_index) = leg_id
        ncong(row_index) = p
        start_pos = comma_pos + 1

        ! Parse vote fields
        do j = 1, nrc_period
          comma_pos = index(line(start_pos:), ',')
          if (comma_pos == 0) then
            token = line(start_pos:)
          else
            token = line(start_pos:start_pos+comma_pos-2)
          endif

          read(token, *, iostat=ios) vote
          if (ios /= 0) vote = 9

          ! Translate: 1=Yea, 6=Nay, 9=Missing
          if (vote >= 1 .and. vote <= 3) then
            ! RCVOTE is stacked by member-period row, but its second index is
            ! the roll-call number *within that member's period*.  RCVOTET is
            ! stacked by roll call, but its second index is the member number
            ! *within that roll call's period*.  The canonical core adds the
            ! period offsets itself.  Applying either offset here a second
            ! time makes the two views disagree from period 2 onward.
            rv1(row_index, j) = 1
            rv9(row_index, j) = 0
            rvt1(rc_off + j, nleg_period) = 1
            rvt9(rc_off + j, nleg_period) = 0
          else if (vote >= 4 .and. vote <= 6) then
            rv1(row_index, j) = 0
            rv9(row_index, j) = 0
            rvt1(rc_off + j, nleg_period) = 0
            rvt9(rc_off + j, nleg_period) = 0
          else
            ! Missing (9 or anything else)
            rv1(row_index, j) = 0
            rv9(row_index, j) = 1
            rvt1(rc_off + j, nleg_period) = 0
            rvt9(rc_off + j, nleg_period) = 1
          endif

          start_pos = start_pos + comma_pos
          if (comma_pos == 0) exit
        enddo

      enddo
      close(u)

      ! Set congress assignments for roll calls
      do j = 1, nrc_period
        icong(rc_off + j) = p
      enddo

      ! Match write_session_file() in the R wrapper: session identifier,
      ! number of roll calls, number of legislator rows.
      mcong(p, 1) = p
      mcong(p, 2) = nrc_period
      mcong(p, 3) = nleg_period

      rc_off = rc_off + nrc_period
      leg_off = leg_off + nleg_period
    enddo

    if (leg_off /= nlegs) then
      write(*,*) 'ERROR: stacked legislator count mismatch', leg_off, nlegs
      stop 1
    endif

    ! Read W-NOMINATE starting coordinates AFTER id1 is populated from vote data
    write(fn, '(A,A)') trim(dir), '/wnominate_coordinates.csv'
    call load_wnominate_coords(fn, nlegs, ndim, id1, xdata)

    ! Unseeded rows remain at the canonical origin.

  end subroutine

  subroutine load_wnominate_coords(fname, nlegs, ndim, id1, xdata)
    character(len=*), intent(in) :: fname
    integer, intent(in) :: nlegs, ndim
    integer, intent(inout) :: id1(nlegs)
    double precision, intent(inout) :: xdata(nlegs, ndim)

    character(len=512) :: line
    integer :: u, ios, leg_id, i
    integer :: nrows, napplied, nbad
    double precision :: c1, c2
    logical :: file_exists

    inquire(file=trim(fname), exist=file_exists)
    if (.not. file_exists) then
      write(*,*) '  WARNING: No W-NOMINATE coordinates file'
      return
    endif

    u = 99
    open(unit=u, file=trim(fname), status='old', action='read', iostat=ios)
    if (ios /= 0) return

    ! Skip header
    read(u, '(A)') line

    nrows = 0
    napplied = 0
    nbad = 0

    do
      read(u, '(A)', iostat=ios) line
      if (ios /= 0) exit
      if (len_trim(line) == 0) cycle
      nrows = nrows + 1

      ! Blank out quotes before the list-directed read. write.csv() emits the
      ! row name quoted ("10808"), and a quoted character constant cannot be
      ! read into an INTEGER: the read fails, and reading straight from the
      ! unit would abandon the whole file on its first data row while still
      ! reporting success. Trailing name/party columns are simply not consumed.
      do i = 1, len(line)
        if (line(i:i) == '"' .or. line(i:i) == '''') line(i:i) = ' '
      enddo
      do i = 1, len(line)
        if (line(i:i) == ',') line(i:i) = ' '
      enddo

      read(line, *, iostat=ios) c1, c2, leg_id
      if (ios /= 0) then
        nbad = nbad + 1
        cycle
      endif

      ! Fill every stacked member-period row for this legislator. Dynamic
      ! panels contain repeated IDs; stopping at the first match would leave
      ! all later periods at an unintended zero start.
      do i = 1, nlegs
        if (id1(i) == leg_id) then
          xdata(i, 1) = c1
          if (ndim >= 2) xdata(i, 2) = c2
          napplied = napplied + 1
        endif
      enddo
    enddo
    close(u)

    ! Report what was APPLIED, not that a file was opened. A success message
    ! for a load that placed zero coordinates is how an unseeded arm passed
    ! for a seeded one.
    write(*,'(A,I0,A,I0,A)') '   W-NOMINATE seed: ', nrows, &
         ' rows read, ', napplied, ' stacked rows seeded'
    if (nbad > 0) then
      write(*,'(A,I0,A)') '   WARNING: ', nbad, ' seed rows could not be parsed'
    endif
    if (napplied == 0) then
      write(*,*) '  WARNING: seed file present but NO coordinates were applied'
    endif
  end subroutine

  subroutine load_terminal_state(dir, nlegs, nrcs, ndim, id1, ncong, &
                                 xdata, zmid, dyn, weights, state_iterations)
    character(len=*), intent(in) :: dir
    integer, intent(in) :: nlegs, nrcs, ndim
    integer, intent(in) :: id1(nlegs), ncong(nlegs)
    double precision, intent(inout) :: xdata(nlegs, ndim)
    double precision, intent(inout) :: zmid(nrcs, ndim), dyn(nrcs, ndim)
    double precision, intent(inout) :: weights(ndim + 1)
    integer, intent(out) :: state_iterations
    character(len=512) :: path

    write(path, '(A,A)') trim(dir), '/summary.csv'
    call load_state_summary(path, ndim, weights, state_iterations)
    write(path, '(A,A)') trim(dir), '/coordinates.csv'
    call load_state_coordinates(path, nlegs, ndim, id1, ncong, xdata)
    write(path, '(A,A)') trim(dir), '/bill_parameters.csv'
    call load_state_bills(path, nrcs, ndim, zmid, dyn)
    write(*,*) '  Loaded complete terminal state'
  end subroutine

  subroutine load_state_summary(path, ndim, weights, state_iterations)
    character(len=*), intent(in) :: path
    integer, intent(in) :: ndim
    double precision, intent(inout) :: weights(ndim + 1)
    integer, intent(out) :: state_iterations
    character(len=2048) :: state_line, key, value_text
    integer :: u, state_ios, comma, found
    logical :: exists
    double precision :: value

    state_iterations = -1

    inquire(file=trim(path), exist=exists)
    if (.not. exists) then
      write(*,*) 'ERROR: Missing state summary ', trim(path)
      stop 1
    endif
    u = 80
    open(unit=u, file=trim(path), status='old', action='read', iostat=state_ios)
    if (state_ios /= 0) stop 1
    read(u, '(A)', iostat=state_ios) state_line
    found = 0
    do
      read(u, '(A)', iostat=state_ios) state_line
      if (state_ios /= 0) exit
      comma = index(state_line, ',')
      if (comma == 0) cycle
      key = adjustl(trim(state_line(1:comma - 1)))
      value_text = adjustl(trim(state_line(comma + 1:)))
      read(value_text, *, iostat=state_ios) value
      if (state_ios /= 0) cycle
      if (trim(key) == 'w2') then
        weights(2) = value
        found = found + 1
      else if (trim(key) == 'beta') then
        weights(ndim + 1) = value
        found = found + 1
      else if (trim(key) == 'iterations') then
        state_iterations = nint(value)
      endif
    enddo
    close(u)
    if (found /= 2) then
      write(*,*) 'ERROR: State summary must contain w2 and beta'
      stop 1
    endif
  end subroutine

  subroutine load_state_coordinates(path, nlegs, ndim, id1, ncong, xdata)
    character(len=*), intent(in) :: path
    integer, intent(in) :: nlegs, ndim
    integer, intent(in) :: id1(nlegs), ncong(nlegs)
    double precision, intent(inout) :: xdata(nlegs, ndim)
    character(len=2048) :: state_line
    integer :: u, state_ios, leg_id, period, row, matched
    double precision :: c1, c2
    logical, allocatable :: loaded(:)
    logical :: exists

    inquire(file=trim(path), exist=exists)
    if (.not. exists) then
      write(*,*) 'ERROR: Missing state coordinates ', trim(path)
      stop 1
    endif
    allocate(loaded(nlegs))
    loaded = .false.
    u = 81
    open(unit=u, file=trim(path), status='old', action='read', iostat=state_ios)
    if (state_ios /= 0) stop 1
    read(u, '(A)', iostat=state_ios) state_line
    do
      read(u, '(A)', iostat=state_ios) state_line
      if (state_ios /= 0) exit
      read(state_line, *, iostat=state_ios) leg_id, period, c1, c2
      if (state_ios /= 0) cycle
      do row = 1, nlegs
        if (id1(row) == leg_id .and. ncong(row) == period) then
          xdata(row, 1) = c1
          if (ndim >= 2) xdata(row, 2) = c2
          loaded(row) = .true.
          exit
        endif
      enddo
    enddo
    close(u)
    matched = count(loaded)
    deallocate(loaded)
    if (matched /= nlegs) then
      write(*,*) 'ERROR: State coordinates incomplete', matched, nlegs
      stop 1
    endif
  end subroutine

  subroutine load_state_bills(path, nrcs, ndim, zmid, dyn)
    character(len=*), intent(in) :: path
    integer, intent(in) :: nrcs, ndim
    double precision, intent(inout) :: zmid(nrcs, ndim), dyn(nrcs, ndim)
    character(len=2048) :: state_line
    integer :: u, state_ios, rollcall_id, row, matched
    double precision :: m1, m2, s1, s2
    logical, allocatable :: loaded(:)
    logical :: exists

    inquire(file=trim(path), exist=exists)
    if (.not. exists) then
      write(*,*) 'ERROR: Missing state bill parameters ', trim(path)
      stop 1
    endif
    allocate(loaded(nrcs))
    loaded = .false.
    u = 82
    open(unit=u, file=trim(path), status='old', action='read', iostat=state_ios)
    if (state_ios /= 0) stop 1
    read(u, '(A)', iostat=state_ios) state_line
    do
      read(u, '(A)', iostat=state_ios) state_line
      if (state_ios /= 0) exit
      read(state_line, *, iostat=state_ios) rollcall_id, m1, m2, s1, s2
      if (state_ios /= 0) cycle
      row = rollcall_id + 1
      if (row < 1 .or. row > nrcs) cycle
      zmid(row, 1) = m1
      dyn(row, 1) = s1
      if (ndim >= 2) then
        zmid(row, 2) = m2
        dyn(row, 2) = s2
      endif
      loaded(row) = .true.
    enddo
    close(u)
    matched = count(loaded)
    deallocate(loaded)
    if (matched /= nrcs) then
      write(*,*) 'ERROR: State bill parameters incomplete', matched, nrcs
      stop 1
    endif
  end subroutine

  subroutine export_results(dir, nlegs, nrcs, ndim, nper, &
                            xdata, zmid, dyn, weights, id1, ncong, &
                            xbiglog, kbiglog, niter, nmodel)
    character(len=*), intent(in) :: dir
    integer, intent(in) :: nlegs, nrcs, ndim, nper, niter, nmodel
    double precision, intent(in) :: xdata(nlegs, ndim)
    double precision, intent(in) :: zmid(nrcs, ndim), dyn(nrcs, ndim)
    double precision, intent(in) :: weights(ndim + 1)
    integer, intent(in) :: id1(nlegs), ncong(nlegs)
    double precision, intent(in) :: xbiglog(nlegs, 2)
    integer, intent(in) :: kbiglog(nlegs, 4)

    character(len=512) :: fn
    integer :: u, i, valid_votes, wrong_predictions
    double precision :: log_likelihood

    log_likelihood = sum(xbiglog(:, 2))
    valid_votes = sum(kbiglog(:, 2))
    wrong_predictions = sum(kbiglog(:, 4))

    ! Export coordinates
    write(fn, '(A,A)') trim(dir), '/coordinates.csv'
    u = 50
    open(unit=u, file=trim(fn), status='replace', action='write')
    write(u, '(A)') 'legislator_id,period,coord1D,coord2D'
    do i = 1, nlegs
      ! Zero is a legitimate coordinate and must remain distinguishable from
      ! an absent member-period row in a reloadable terminal state.
      write(u, '(I0,A,I0,A,F18.15,A,F18.15)') &
        id1(i), ',', ncong(i), ',', xdata(i,1), ',', xdata(i,2)
    enddo
    close(u)
    write(*,*) '  Wrote ', trim(fn)

    ! Export bill parameters
    write(fn, '(A,A)') trim(dir), '/bill_parameters.csv'
    open(unit=u, file=trim(fn), status='replace', action='write')
    write(u, '(A)') 'rollcall_id,midpoint1D,midpoint2D,spread1D,spread2D'
    do i = 1, nrcs
      write(u, '(I0,A,F18.15,A,F18.15,A,F18.15,A,F18.15)') &
        i-1, ',', zmid(i,1), ',', zmid(i,2), ',', dyn(i,1), ',', dyn(i,2)
    enddo
    close(u)
    write(*,*) '  Wrote ', trim(fn)

    ! Export summary
    write(fn, '(A,A)') trim(dir), '/summary.csv'
    open(unit=u, file=trim(fn), status='replace', action='write')
    write(u, '(A)') 'parameter,value'
    write(u, '(A,F24.12)') 'log_likelihood,', log_likelihood
    ! These values are continuation state, not presentation-only summaries.
    ! Six decimals measurably change later dynamic cycles.
    write(u, '(A,F24.15)') 'w1,', weights(1)
    write(u, '(A,F24.15)') 'w2,', weights(2)
    write(u, '(A,F24.15)') 'beta,', weights(ndim+1)
    write(u, '(A,I0)') 'iterations,', niter
    write(u, '(A,I0)') 'valid_votes,', valid_votes
    write(u, '(A,I0)') 'correct_classifications,', &
                       valid_votes - wrong_predictions
    write(u, '(A,I0)') 'temporal_model,', nmodel
    write(u, '(A,I0)') 'dimensions,', ndim
    write(u, '(A,I0)') 'periods,', nper
    close(u)
    write(*,*) '  Wrote ', trim(fn)
  end subroutine

end program dwnominate_standalone
